"""Scoring API request/response schemas using Pydantic v2."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RiskScoreRequest(BaseModel):
    """POST /v1/risk/score request body.

    Requires Idempotency-Key header for deduplication.
    All fields are validated at the schema level.
    """

    transaction_id: str = Field(..., min_length=1, max_length=255, description="Unique transaction ID")
    customer_id: str = Field(..., min_length=1, max_length=255, description="Customer ID")
    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$", description="ISO 4217 currency code")
    merchant_id: str = Field(..., min_length=1, max_length=255, description="Merchant ID")
    merchant_category: Optional[str] = Field(None, max_length=255, description="ISO 18245 merchant category code")
    merchant_country: Optional[str] = Field(None, pattern="^[A-Z]{2}$", description="ISO 3166-1 country code")

    model_config = {"title": "RiskScoreRequest"}


class RiskScoreResponse(BaseModel):
    """POST /v1/risk/score success response (2xx).

    Contains risk assessment and recommendation for downstream systems.
    All decisions are based on rule engine evaluation.
    """

    request_id: str = Field(..., description="Request tracking ID from Idempotency-Key")
    transaction_id: str = Field(..., description="Transaction ID (echo)")
    
    # Risk assessment
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score [0.0, 1.0]")
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$", description="Risk classification")
    decision: str = Field(..., pattern="^(APPROVE|REVIEW|DECLINE)$", description="Scoring decision")
    
    # Reason codes for FCRA adverse action
    reason_codes: list[str] = Field(
        default_factory=list,
        description="FCRA-compliant reason codes for decline/review decisions"
    )
    
    # Execution metadata
    processing_ms: int = Field(..., ge=0, description="Processing time in milliseconds")
    engine_version: str = Field(default="1.0.0", description="Scoring engine version")

    model_config = {
        "title": "RiskScoreResponse",
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "transaction_id": "txn_abc123",
                    "risk_score": 0.25,
                    "risk_level": "LOW",
                    "decision": "APPROVE",
                    "reason_codes": [],
                    "processing_ms": 45,
                    "engine_version": "1.0.0",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response for all failure scenarios (4xx, 5xx)."""

    error_code: str = Field(..., description="Machine-readable error type (e.g., VALIDATION_ERROR, INTERNAL_SERVER_ERROR)")
    message: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(None, description="Request ID if available (from request state)")
    details: Optional[dict] = Field(None, description="Additional error context")

    model_config = {
        "title": "ErrorResponse",
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid currency code. Expected ISO 4217 format.",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "details": {"field": "currency", "value": "USDA"}
                }
            ]
        }
    }
