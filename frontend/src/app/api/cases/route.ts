/**
 * BFF Route Handler: GET /api/cases
 *
 * Example of the BFF pattern:
 * 1. Receive request from browser
 * 2. Verify session + scope (server-side)
 * 3. Proxy to backend with authorization header
 * 4. Return response to browser (never expose raw JWT)
 *
 * The browser NEVER calls the backend directly.
 */

import { NextRequest, NextResponse } from "next/server";
import { authorizeRoute, fetchBackend } from "@/lib/bff";

export async function GET(request: NextRequest): Promise<NextResponse> {
  // Verify auth + scope
  const { session, error } = await authorizeRoute("cases:read");
  if (error) return error;

  // Proxy to backend
  try {
    const response = await fetchBackend("/v1/cases", session, {
      method: "GET",
    });

    if (!response.ok) {
      return NextResponse.json(
        { error_code: "BACKEND_ERROR", message: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to reach backend" },
      { status: 503 }
    );
  }
}

/**
 * POST /api/cases — create or assign a case.
 * Requires cases:write scope.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const { session, error } = await authorizeRoute("cases:write");
  if (error) return error;

  try {
    const body = await request.json();
    const response = await fetchBackend("/v1/cases", session, {
      method: "POST",
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error_code: "BACKEND_ERROR", message: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to reach backend" },
      { status: 503 }
    );
  }
}
