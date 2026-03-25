/**
 * BFF Health check endpoint: GET /api/health
 *
 * Used by:
 * - @darius: Docker healthcheck (HEALTHCHECK in Dockerfile)
 * - Load balancers / Kubernetes readiness probe
 * - Frontend status monitoring
 *
 * This endpoint checks:
 * 1. The Next.js server is running
 * 2. Optionally, the backend is reachable (if BACKEND_URL is set)
 */

import { NextResponse } from "next/server";
import { serverHealthCheck, ApiError } from "@/lib/api-client";

interface FrontendHealthResponse {
  readonly status: "healthy" | "degraded" | "unhealthy";
  readonly timestamp: string;
  readonly version: string;
  readonly backend: {
    readonly status: "healthy" | "unreachable";
    readonly version?: string;
    readonly error?: string;
  };
}

export async function GET(): Promise<NextResponse<FrontendHealthResponse>> {
  let backendStatus: FrontendHealthResponse["backend"] = {
    status: "unreachable",
  };

  try {
    const backendHealth = await serverHealthCheck();
    backendStatus = {
      status: "healthy",
      version: backendHealth.version,
    };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : "Unknown error";

    backendStatus = {
      status: "unreachable",
      error: errorMessage,
    };
  }

  const overallStatus =
    backendStatus.status === "healthy" ? "healthy" : "degraded";

  const response: FrontendHealthResponse = {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    version: "1.0.0",
    backend: backendStatus,
  };

  const httpStatus = overallStatus === "healthy" ? 200 : 503;

  return NextResponse.json(response, { status: httpStatus });
}
