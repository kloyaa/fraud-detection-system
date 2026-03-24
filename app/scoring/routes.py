"""Scoring API routes - POST /v1/risk/score skeleton.

This is the entry point for transaction risk scoring.
Requires Idempotency-Key header for all requests.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.engine import get_db_session
from app.scoring.schemas import RiskScoreRequest, RiskScoreResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/risk", tags=["scoring"])


@router.post("/score", response_model=RiskScoreResponse, status_code=200)
async def score_transaction(
    request_body: RiskScoreRequest,
    session: AsyncSession = Depends(get_db_session),
    idempotency_key: str | None = Header(
        None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
) -> RiskScoreResponse:
    """Score a transaction for fraud risk.

    Requires Idempotency-Key header to ensure idempotency across retries.
    Returns the same response for identical request bodies + key combination.

    Args:
        request_body: Transaction details
        session: Database session (injected)
        idempotency_key: UUID or unique string for request deduplication

    Returns:
        RiskScoreResponse with score, tier, and decision

    Raises:
        HTTPException 422: Validation error or missing Idempotency-Key
        HTTPException 400: Business logic rejection (e.g. invalid currency)
        HTTPException 500: Unexpected error
    """
    # ❌ TODO: Validate Idempotency-Key + check Redis for existing result
    # ❌ TODO: Call rule engine for initial scoring (blocking call in Celery)
    # ❌ TODO: Write audit log to Cassandra
    # ❌ TODO: Cache result in Redis with 24h TTL for idempotency

    logger.info(
        "score_request",
        transaction_id=request_body.transaction_id,
        customer_id=request_body.customer_id,
        amount_cents=request_body.amount_cents,
    )

    # SKELETON: Return mock score for now
    # Real implementation plugs into rule engine
    return RiskScoreResponse(
        request_id=uuid4(),
        risk_score=Decimal("0.3500"),
        risk_tier="MEDIUM",
        decision="REVIEW",
    )
