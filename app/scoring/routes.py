"""Scoring API routes - POST /v1/risk/score implementation.

This is the entry point for transaction risk scoring.
Requires Idempotency-Key header for all requests.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.engine import get_db_session
from app.scoring.schemas import RiskScoreRequest, RiskScoreResponse, ErrorResponse
from app.scoring.service import ScoringService

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/risk", tags=["scoring"])


@router.post(
    "/score",
    response_model=RiskScoreResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Business logic error"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    status_code=200,
)
async def score_transaction(
    request_body: RiskScoreRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    idempotency_key: str | None = Header(
        None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
) -> RiskScoreResponse:
    """Score a transaction for fraud risk.

    Requires Idempotency-Key header for request deduplication.
    Returns the same response for identical request bodies + key combination.

    Request body:
        - transaction_id: str (1-255 chars)
        - customer_id: str (1-255 chars)
        - amount_cents: int (> 0)
        - currency: str (ISO 4217, default USD)
        - merchant_id: str (1-255 chars)
        - merchant_category: str optional (ISO 18245 code)
        - merchant_country: str optional (ISO 3166-1 code)

    Returns:
        - request_id: Request tracing ID
        - transaction_id: Echo of input
        - risk_score: float [0.0, 1.0]
        - risk_level: LOW | MEDIUM | HIGH | CRITICAL
        - decision: APPROVE | REVIEW | DECLINE
        - reason_codes: list[str] (FCRA-compliant)
        - processing_ms: int (execution time)
        - engine_version: str

    Errors:
        - 422: Validation failed (schema validation by FastAPI)
        - 400: Business logic error
        - 500: Unexpected server error

    Example:
        POST /v1/risk/score
        Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
        Content-Type: application/json

        {
            "transaction_id": "txn_abc123",
            "customer_id": "cust_xyz789",
            "amount_cents": 10000,
            "currency": "USD",
            "merchant_id": "mch_foo",
            "merchant_category": "5411",
            "merchant_country": "US"
        }

    Response: 200 OK
        {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "transaction_id": "txn_abc123",
            "risk_score": 0.15,
            "risk_level": "LOW",
            "decision": "APPROVE",
            "reason_codes": [],
            "processing_ms": 42,
            "engine_version": "1.0.0"
        }
    """
    try:
        # Get request ID from header (set by RequestIDMiddleware)
        request_id = request.state.request_id

        # Initialize service layer
        service = ScoringService(session)

        # Score the transaction
        response = await service.score_transaction(
            request=request_body,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

        # Commit database changes (assessment recorded)
        await session.commit()

        logger.info(
            "score_endpoint_success",
            transaction_id=request_body.transaction_id,
            risk_level=response.risk_level,
            decision=response.decision,
        )

        return response

    except ValueError as e:
        logger.error(
            "score_endpoint_validation_error",
            error=str(e),
            transaction_id=request_body.transaction_id,
        )
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message=str(e),
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    except Exception as e:
        logger.error(
            "score_endpoint_error",
            error=str(e),
            error_type=type(e).__name__,
            transaction_id=request_body.transaction_id,
        )
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred while scoring the transaction.",
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )
