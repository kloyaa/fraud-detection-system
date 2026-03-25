import { NextResponse } from "next/server";

/**
 * Health check endpoint for Docker healthcheck and load balancers.
 * Returns 200 OK if the frontend is running.
 */
export function GET(): NextResponse {
  return NextResponse.json({ status: "ok" });
}
