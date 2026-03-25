/**
 * RAS API TypeScript types — manually derived from @sofia's Pydantic schemas.
 *
 * Source of truth: app/scoring/schemas.py (RiskScoreRequest, RiskScoreResponse, ErrorResponse)
 * Source of truth: app/health/routes.py (HealthResponse)
 *
 * Once @sofia publishes the stable OpenAPI spec, these will be replaced by
 * auto-generated types via `pnpm generate:types` (openapi-typescript).
 * Until then, any backend schema change MUST be reflected here manually.
 */

// ---------------------------------------------------------------------------
// Enum-like unions — matches FastAPI regex patterns exactly
// ---------------------------------------------------------------------------

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type Decision = "APPROVE" | "REVIEW" | "DECLINE";

// ---------------------------------------------------------------------------
// POST /v1/risk/score — Request
// ---------------------------------------------------------------------------

export interface RiskScoreRequest {
  /** Unique transaction ID (1-255 chars) */
  readonly transaction_id: string;
  /** Customer ID (1-255 chars) */
  readonly customer_id: string;
  /** Amount in cents (> 0) */
  readonly amount_cents: number;
  /** ISO 4217 currency code (3 uppercase letters, default "USD") */
  readonly currency: string;
  /** Merchant ID (1-255 chars) */
  readonly merchant_id: string;
  /** ISO 18245 merchant category code (optional, max 255 chars) */
  readonly merchant_category?: string | null;
  /** ISO 3166-1 alpha-2 country code (optional) */
  readonly merchant_country?: string | null;
}

// ---------------------------------------------------------------------------
// POST /v1/risk/score — Response
// ---------------------------------------------------------------------------

export interface RiskScoreResponse {
  /** Request tracking ID (from Idempotency-Key header) */
  readonly request_id: string;
  /** Transaction ID (echo of input) */
  readonly transaction_id: string;
  /** Risk score in [0.0, 1.0] */
  readonly risk_score: number;
  /** Risk classification */
  readonly risk_level: RiskLevel;
  /** Scoring decision */
  readonly decision: Decision;
  /** FCRA-compliant reason codes for decline/review decisions */
  readonly reason_codes: readonly string[];
  /** Processing time in milliseconds (>= 0) */
  readonly processing_ms: number;
  /** Scoring engine version */
  readonly engine_version: string;
}

// ---------------------------------------------------------------------------
// Error response (4xx / 5xx)
// ---------------------------------------------------------------------------

export interface ErrorResponse {
  /** Machine-readable error type (e.g., VALIDATION_ERROR) */
  readonly error_code: string;
  /** Human-readable error message */
  readonly message: string;
  /** Request ID if available */
  readonly request_id?: string | null;
  /** Additional error context */
  readonly details?: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// GET /v1/health — Response
// ---------------------------------------------------------------------------

export interface HealthResponse {
  readonly status: string;
  readonly timestamp: string;
  readonly version: string;
}
