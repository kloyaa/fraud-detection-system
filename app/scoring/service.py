"""Scoring service layer - business logic for risk assessment.

Coordinates between API layer and rule engine.
Handles scoring, persistence, and audit logging.
"""

import time
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import RiskAssessment
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
        3. Persist decision for audit trail
        4. Return response

        Args:
            request: Validated scoring request
            request_id: Trace ID (from X-Request-ID header)
            idempotency_key: Optional deduplication key (from Idempotency-Key header)

        Returns:
            Risk score response with decision and reasons

        Raises:
            ValueError: If validation fails
        """
        start_time = time.time()

        # Step 1: Check idempotency cache (if key provided)
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

        # Step 3: Persist to database for audit trail
        assessment = await self._persist_assessment(
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

        logger.info(
            "scoring_complete",
            transaction_id=request.transaction_id,
            risk_level=response.risk_level,
            decision=response.decision,
            processing_ms=processing_ms,
        )

        return response

    async def _get_cached_assessment(self, idempotency_key: str) -> Optional[RiskScoreResponse]:
        """Check database for existing idempotency key.

        In production, this would check Redis first; we use DB for simplicity.

        Args:
            idempotency_key: Deduplication key

        Returns:
            Cached response if found, None otherwise
        """
        stmt = select(RiskAssessment).where(
            RiskAssessment.idempotency_key == idempotency_key
        )
        result = await self.db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            return None

        # Reconstruct response from cached assessment
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
        """Persist scoring decision for audit trail.

        Args:
            request: Original scoring request
            score_result: Result from rules engine
            request_id: Trace ID
            idempotency_key: Deduplication key

        Returns:
            Persisted RiskAssessment record
        """
        assessment = RiskAssessment(
            idempotency_key=idempotency_key,
            transaction_id=request.transaction_id,
            customer_id=request.customer_id,
            amount=request.amount_cents / 100,  # Convert cents to dollars
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
        await self.db.flush()  # Flush to get ID without commit

        logger.info(
            "assessment_persisted",
            assessment_id=assessment.id,
            transaction_id=assessment.transaction_id,
        )

        return assessment
