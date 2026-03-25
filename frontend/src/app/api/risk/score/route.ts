/**
 * BFF Route Handler: POST /api/risk/score
 *
 * Security architecture (coordinated with @priya):
 * 1. Browser sends request to THIS handler (not the backend directly)
 * 2. This handler validates the session (NextAuth)
 * 3. This handler validates the request body (Zod)
 * 4. This handler forwards to backend FastAPI at BACKEND_URL/v1/risk/score
 * 5. This handler validates the backend response (Zod)
 * 6. This handler returns the validated response to the browser
 *
 * The Idempotency-Key header is forwarded from the client to the backend.
 * The browser NEVER calls the backend directly.
 *
 * @sofia: This calls POST BACKEND_URL/v1/risk/score with the Idempotency-Key
 * header forwarded. Request/response shapes match app/scoring/schemas.py.
 */

import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { serverScoreTransaction, ApiError } from "@/lib/api-client";
import { RiskScoreRequestSchema } from "@/lib/zod-schemas";
import type { ErrorResponse } from "@/types/ras-api";

export async function POST(request: NextRequest): Promise<NextResponse> {
  // -------------------------------------------------------------------------
  // 1. Authenticate — reject unauthenticated requests
  // -------------------------------------------------------------------------
  const session = await auth();
  if (!session?.user) {
    const errorBody: ErrorResponse = {
      error_code: "UNAUTHORIZED",
      message: "Authentication required. Please sign in.",
      request_id: null,
      details: null,
    };
    return NextResponse.json(errorBody, { status: 401 });
  }

  // -------------------------------------------------------------------------
  // 2. Extract and validate Idempotency-Key header
  // -------------------------------------------------------------------------
  const idempotencyKey = request.headers.get("Idempotency-Key");
  if (!idempotencyKey) {
    const errorBody: ErrorResponse = {
      error_code: "MISSING_HEADER",
      message: "Idempotency-Key header is required.",
      request_id: null,
      details: { header: "Idempotency-Key" },
    };
    return NextResponse.json(errorBody, { status: 400 });
  }

  // -------------------------------------------------------------------------
  // 3. Parse and validate request body with Zod
  // -------------------------------------------------------------------------
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    const errorBody: ErrorResponse = {
      error_code: "INVALID_JSON",
      message: "Request body must be valid JSON.",
      request_id: null,
      details: null,
    };
    return NextResponse.json(errorBody, { status: 400 });
  }

  const parsed = RiskScoreRequestSchema.safeParse(body);
  if (!parsed.success) {
    const errorBody: ErrorResponse = {
      error_code: "VALIDATION_ERROR",
      message: "Request body validation failed.",
      request_id: null,
      details: {
        issues: parsed.error.issues.map((issue) => ({
          path: issue.path.join("."),
          message: issue.message,
        })),
      },
    };
    return NextResponse.json(errorBody, { status: 422 });
  }

  // -------------------------------------------------------------------------
  // 4. Forward to backend via server-side API client
  // -------------------------------------------------------------------------
  try {
    const response = await serverScoreTransaction(parsed.data, idempotencyKey);
    return NextResponse.json(response, { status: 200 });
  } catch (error) {
    if (error instanceof ApiError) {
      const errorBody: ErrorResponse = {
        error_code: error.errorCode,
        message: error.message,
        request_id: error.requestId,
        details: error.details,
      };
      return NextResponse.json(errorBody, { status: error.status });
    }

    // Unexpected error — do not leak internal details
    const errorBody: ErrorResponse = {
      error_code: "INTERNAL_ERROR",
      message: "An unexpected error occurred while processing the request.",
      request_id: null,
      details: null,
    };
    return NextResponse.json(errorBody, { status: 500 });
  }
}
