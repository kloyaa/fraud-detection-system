/**
 * Edge Middleware — CSP nonce injection.
 *
 * Per @priya security review (2026-03-25):
 * - Generates 128-bit random nonce per request
 * - Stores nonce in request headers for app to read via headers()
 * - Sets Content-Security-Policy response header with nonce
 * - CSP: script-src 'self' 'nonce-{random}' 'strict-dynamic'
 * - No `unsafe-inline` for scripts (Tailwind CSS allowlisted in style-src)
 *
 * NextAuth route protection handled via getServerSession() in layout/routes.
 */

import { NextRequest, NextResponse } from "next/server";

function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

function buildCspHeader(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
}

export function middleware(request: NextRequest): NextResponse {
  const nonce = generateNonce();
  const csp = buildCspHeader(nonce);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-CSP-Nonce-Test", nonce); // Test header to verify middleware runs
  return response;
}

export const config = {
  matcher: [
    "/dashboard",
    "/api/:path*",
  ],
};
