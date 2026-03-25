/**
 * Typed API client for BFF Route Handlers.
 *
 * Architecture (coordinated with @priya and @sofia):
 * - Browser calls Next.js Route Handlers at /api/*
 * - Route Handlers call backend FastAPI at BACKEND_URL (server-side only)
 * - Browser NEVER calls the backend directly
 *
 * This module provides:
 * 1. Server-side functions for Route Handlers to call the backend
 * 2. Client-side functions for components to call the BFF
 *
 * All responses are validated at runtime with Zod schemas.
 */

import {
  HealthResponseSchema,
  RiskScoreResponseSchema,
  ErrorResponseSchema,
} from "@/lib/zod-schemas";
import type { RiskScoreRequest, RiskScoreResponse, HealthResponse } from "@/types/ras-api";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Backend URL — only available server-side (no NEXT_PUBLIC_ prefix).
 * In Docker: http://app:8000
 * Local dev: http://localhost:8000
 */
function getBackendUrl(): string {
  const url = process.env.BACKEND_URL;
  if (!url) {
    throw new Error(
      "BACKEND_URL environment variable is not set. " +
      "This should be set in .env.local (local dev) or docker-compose.yml.",
    );
  }
  return url;
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errorCode: string,
    public readonly requestId?: string | null,
    public readonly details?: Record<string, unknown> | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleErrorResponse(response: Response): Promise<never> {
  let errorMessage = `Backend responded with ${String(response.status)}`;
  let errorCode = "UNKNOWN_ERROR";
  let requestId: string | null = null;
  let details: Record<string, unknown> | null = null;

  try {
    const body: unknown = await response.json();
    const parsed = ErrorResponseSchema.safeParse(body);
    if (parsed.success) {
      errorMessage = parsed.data.message;
      errorCode = parsed.data.error_code;
      requestId = parsed.data.request_id ?? null;
      details = parsed.data.details ?? null;
    }
  } catch {
    // Response body was not valid JSON — use the default message
  }

  throw new ApiError(errorMessage, response.status, errorCode, requestId, details);
}

// ---------------------------------------------------------------------------
// Server-side: Route Handler → Backend FastAPI
// ---------------------------------------------------------------------------

/**
 * Score a transaction via the backend.
 * Called from the BFF Route Handler at /api/risk/score.
 *
 * @param request - Risk score request body
 * @param idempotencyKey - Idempotency-Key header value (forwarded from client)
 * @returns Validated RiskScoreResponse
 */
export async function serverScoreTransaction(
  request: RiskScoreRequest,
  idempotencyKey: string,
): Promise<RiskScoreResponse> {
  const backendUrl = getBackendUrl();

  const response = await fetch(`${backendUrl}/v1/risk/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(request),
    /** No cache for scoring requests — always fresh */
    cache: "no-store",
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  const body: unknown = await response.json();
  const parsed = RiskScoreResponseSchema.safeParse(body);

  if (!parsed.success) {
    throw new ApiError(
      `Backend response failed Zod validation: ${parsed.error.message}`,
      502,
      "RESPONSE_VALIDATION_ERROR",
    );
  }

  return parsed.data;
}

/**
 * Check backend health.
 * Called from the BFF health endpoint at /api/health.
 */
export async function serverHealthCheck(): Promise<HealthResponse> {
  const backendUrl = getBackendUrl();

  const response = await fetch(`${backendUrl}/v1/health`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  const body: unknown = await response.json();
  const parsed = HealthResponseSchema.safeParse(body);

  if (!parsed.success) {
    throw new ApiError(
      `Health response failed Zod validation: ${parsed.error.message}`,
      502,
      "RESPONSE_VALIDATION_ERROR",
    );
  }

  return parsed.data;
}

// ---------------------------------------------------------------------------
// Client-side: Browser → BFF Route Handlers
// ---------------------------------------------------------------------------

/**
 * Score a transaction via the BFF.
 * Called from Client Components — hits /api/risk/score (NOT the backend directly).
 */
export async function clientScoreTransaction(
  request: RiskScoreRequest,
  idempotencyKey: string,
): Promise<RiskScoreResponse> {
  const response = await fetch("/api/risk/score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  const body: unknown = await response.json();
  const parsed = RiskScoreResponseSchema.safeParse(body);

  if (!parsed.success) {
    throw new ApiError(
      `BFF response failed Zod validation: ${parsed.error.message}`,
      502,
      "RESPONSE_VALIDATION_ERROR",
    );
  }

  return parsed.data;
}
