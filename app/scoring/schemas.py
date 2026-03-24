"""Scoring API request/response schemas using Pydantic v2."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RiskScoreRequest(BaseModel):
    """POST /v1/risk/score request body.

    Requires Idempotency-Key header for idempotency (stored in Redis).
    """

    transaction_id: str = Field(..., min_length=1, max_length=255)
    """Unique transaction identifier from upstream system."""

    customer_id: str = Field(..., min_length=1, max_length=255)
    """Customer identifier for risk assessment."""

    amount_cents: int = Field(..., gt=0)
    """Transaction amount in cents (e.g., 10000 = $100.00)."""

    merchant_id: str = Field(..., min_length=1, max_length=255)
    """Merchant identifier."""

    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    """ISO 4217 currency code."""

    model_config = {"title": "RiskScoreRequest"}


class RiskScoreResponse(BaseModel):
    """POST /v1/risk/score success response."""

    request_id: UUID
    """Request tracking ID from idempotency key."""

    risk_score: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    """Risk score from [0.0000, 1.0000] where 1.0 = highest fraud risk."""

    risk_tier: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    """Risk classification tier."""

    decision: str = Field(..., pattern="^(APPROVE|REVIEW|DECLINE)$")
    """Initial scoring decision (may be overridden by rules engine)."""

    model_config = {"title": "RiskScoreResponse"}


class ErrorResponse(BaseModel):
    """Error response (422 validation, 400 business logic, 500 unexpected)."""

    error_code: str
    """Machine-readable error type (e.g., IDEMPOTENCY_KEY_CONFLICT)."""

    message: str
    """Human-readable error message."""

    request_id: str
    """Request tracking ID for debugging."""

    model_config = {"title": "ErrorResponse"}
