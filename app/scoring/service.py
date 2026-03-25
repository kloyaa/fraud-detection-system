"""Scoring service layer - business logic for risk assessment.

Coordinates between API layer and rule engine.
Handles scoring, persistence, Kafka publish, and Cassandra audit log.

Execution order (per Sprint 1 completion criteria):
  1. Check idempotency cache (DB lookup by idempotency_key)
  2. Run scoring rules engine
  3. Persist to PostgreSQL (risk_assessments — idempotency + audit)
  4. Persist to risk_decisions (Kafka-aligned analytics record)
  5. Return response to client (< 100ms P95 target)
  6. Background: publish to Kafka risk.decisions topic (fire-and-forget)
  7. Background: write to Cassandra risk_events audit log (fire-and-forget)

Steps 6 and 7 are launched with asyncio.create_task() after the response
is returned. Client is never blocked by Kafka or Cassandra latency.
"""

import asyncio
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cassandra.client import write_risk_event
from app.core.logging import get_logger
from app.db.models import RiskAssessment, RiskDecision
from app.kafka.producer import publish_risk_decision
from app.scoring.rules import ScoringRulesEngine
from app.scoring.schemas import RiskScoreRequest, RiskScoreResponse

logger = get_logger(__name__)


class ScoringService:
    """Orchestrates the risk scoring workflow."""

    def __init__(self, db_session: AsyncSession, rules_engine: Optional[ScoringRulesEngine] = None):
        self.db = db_session
        self.rules_engine = rules_engine or ScoringRulesEngine()

    async def score_transaction(
        self,
        request: RiskScoreRequest,
        request_id: str,
        idempotency_key: Optional[str] = None,
    ) -> RiskScoreResponse:
        """Score a transaction end-to-end.

        Steps:
        1. Check for existing assessment (idempotency)
        2. Run scoring rules
        3. Persist to risk_assessments (idempotency + audit)
        4. Persist to risk_decisions (Kafka-aligned record)
        5. Return response
        6. Background: Kafka publish (risk.decisions)
        7. Background: Cassandra audit log (risk_events)

        Args:
            request: Validated scoring request
            request_id: Trace ID (from X-Request-ID header)
            idempotency_key: Optional deduplication key (from Idempotency-Key header)

        Returns:
            Risk score response with decision and reasons
        """
        start_time = time.time()

        # Step 1: Check idempotency cache
        if idempotency_key:
            cached = await self._get_cached_assessment(idempotency_key)
            if cached:
                logger.info(
                    "scoring_cache_hit",
                    idempotency_key=idempotency_key,
                    transaction_id=request.transaction_id,
                )
                return cached

        # Step 2: Score transaction with rules engine
        score_result = self.rules_engine.evaluate(request)

        # Step 3: Persist to risk_assessments (idempotency + legacy audit)
        await self._persist_assessment(
            request=request,
            score_result=score_result,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

        # Step 4: Build response
        processing_ms = int((time.time() - start_time) * 1000)
        response = RiskScoreResponse(
            request_id=request_id,
            transaction_id=request.transaction_id,
            risk_score=score_result["score"],
            risk_level=score_result["level"],
            decision=score_result["decision"],
            reason_codes=score_result.get("reason_codes", []),
            processing_ms=processing_ms,
            engine_version="1.0.0",
        )

        # Step 5: Persist to risk_decisions (Kafka-aligned analytics record)
        score_int = int(score_result["score"] * 1000)  # Convert 0.0–1.0 → 0–1000
        requires_review = score_result["decision"] == "REVIEW"
        rules_triggered = score_result.get("reason_codes", [])

        risk_decision = RiskDecision(
            request_id=request_id,
            customer_id=request.customer_id,
            merchant_id=request.merchant_id,
            amount_cents=request.amount_cents,
            currency=request.currency,
            score=score_int,
            decision=score_result["decision"],
            rules_triggered=",".join(rules_triggered),
            processing_ms=processing_ms,
            requires_review=requires_review,
        )
        self.db.add(risk_decision)
        await self.db.flush()

        logger.info(
            "scoring_complete",
            transaction_id=request.transaction_id,
            risk_level=response.risk_level,
            decision=response.decision,
            processing_ms=processing_ms,
        )

        # Steps 6 + 7: Fire-and-forget background tasks
        # These do NOT block the response — client gets the decision first
        asyncio.create_task(
            self._publish_to_kafka(
                request_id=request_id,
                customer_id=request.customer_id,
                merchant_id=request.merchant_id,
                amount_cents=request.amount_cents,
                currency=request.currency,
                score_int=score_int,
                decision=score_result["decision"],
                rules_triggered=rules_triggered,
                processing_ms=processing_ms,
                requires_review=requires_review,
                risk_decision_id=risk_decision.id,
            )
        )

        asyncio.create_task(
            self._write_cassandra_audit(
                request_id=request_id,
                customer_id=request.customer_id,
                merchant_id=request.merchant_id,
                amount_cents=request.amount_cents,
                currency=request.currency,
                score_int=score_int,
                decision=score_result["decision"],
                rules_triggered=rules_triggered,
                processing_ms=processing_ms,
            )
        )

        return response

    async def _get_cached_assessment(self, idempotency_key: str) -> Optional[RiskScoreResponse]:
        """Check database for existing idempotency key."""
        stmt = select(RiskAssessment).where(
            RiskAssessment.idempotency_key == idempotency_key
        )
        result = await self.db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            return None

        return RiskScoreResponse(
            request_id=assessment.request_id or idempotency_key,
            transaction_id=assessment.transaction_id,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            decision=assessment.decision,
            reason_codes=assessment.reason_codes.split(",") if assessment.reason_codes else [],
            processing_ms=assessment.processing_ms,
            engine_version=assessment.engine_version or "1.0.0",
        )

    async def _persist_assessment(
        self,
        request: RiskScoreRequest,
        score_result: dict,
        request_id: str,
        idempotency_key: Optional[str],
    ) -> RiskAssessment:
        """Persist scoring decision to risk_assessments for idempotency + audit."""
        assessment = RiskAssessment(
            idempotency_key=idempotency_key,
            transaction_id=request.transaction_id,
            customer_id=request.customer_id,
            amount=request.amount_cents / 100,
            currency=request.currency,
            merchant_category=request.merchant_category,
            merchant_country=request.merchant_country,
            risk_score=score_result["score"],
            risk_level=score_result["level"],
            decision=score_result["decision"],
            reason_codes=",".join(score_result.get("reason_codes", [])),
            engine_version="1.0.0",
            request_id=request_id,
        )

        self.db.add(assessment)
        await self.db.flush()

        logger.info(
            "assessment_persisted",
            assessment_id=assessment.id,
            transaction_id=assessment.transaction_id,
        )

        return assessment

    async def _publish_to_kafka(
        self,
        request_id: str,
        customer_id: str,
        merchant_id: str,
        amount_cents: int,
        currency: str,
        score_int: int,
        decision: str,
        rules_triggered: list[str],
        processing_ms: int,
        requires_review: bool,
        risk_decision_id: int,
    ) -> None:
        """Background task: publish decision to Kafka risk.decisions topic."""
        offset = await publish_risk_decision(
            request_id=request_id,
            customer_id=customer_id,
            merchant_id=merchant_id,
            amount_cents=amount_cents,
            currency=currency,
            score_int=score_int,
            decision=decision,
            rules_triggered=rules_triggered,
            processing_ms=processing_ms,
            requires_review=requires_review,
        )

        if offset is not None:
            # Update published_to_kafka flag — best-effort, use a fresh session
            # (the request session may already be closed by this point)
            from app.db.engine import get_db
            try:
                async with get_db() as session:
                    from sqlalchemy import update
                    await session.execute(
                        update(RiskDecision)
                        .where(RiskDecision.id == risk_decision_id)
                        .values(published_to_kafka=True, kafka_offset=offset)
                    )
            except Exception as e:
                logger.warning("kafka_offset_update_failed", error=str(e))

    async def _write_cassandra_audit(
        self,
        request_id: str,
        customer_id: str,
        merchant_id: str,
        amount_cents: int,
        currency: str,
        score_int: int,
        decision: str,
        rules_triggered: list[str],
        processing_ms: int,
    ) -> None:
        """Background task: write event to Cassandra risk_events audit log."""
        await write_risk_event(
            customer_id=customer_id,
            request_id=request_id,
            merchant_id=merchant_id,
            amount_cents=amount_cents,
            currency=currency,
            score=score_int,
            decision=decision,
            rules_triggered=rules_triggered,
            processing_ms=processing_ms,
        )
