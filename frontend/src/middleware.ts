/**
 * Next.js Edge Middleware — CSP nonce injection.
 *
 * Generates a cryptographically random nonce on every request and injects it
 * into the Content-Security-Policy header. Next.js 14 reads the `x-nonce`
 * request header and automatically adds `nonce="..."` to every inline script
 * it renders (hydration, RSC payload, etc.), satisfying `script-src 'self'`
 * without requiring `'unsafe-inline'`.
 *
 * Agreed with @priya: CSP is dynamic (nonce-based), not static. Static hashes
 * are not viable for SSR pages where Next.js regenerates script content.
 *
 * The static security headers (X-Frame-Options, HSTS, etc.) remain in
 * next.config.js — only the CSP moves here because it needs the dynamic nonce.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest): NextResponse {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");

  // Pass nonce to the app via request header — Next.js reads x-nonce and
  // injects it into its own inline scripts automatically.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  // Set CSP on the response so the browser enforces it.
  response.headers.set("Content-Security-Policy", csp);

  return response;
}

/**
 * Run middleware on all routes except:
 * - _next/static  — immutable static assets; no inline scripts, no need for CSP header
 * - _next/image   — image optimisation responses
 * - favicon.ico   — static asset
 *
 * The `missing` condition skips Next.js prefetch requests, which are data
 * fetches that never render HTML and don't need a CSP header.
 */
export const config = {
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
