/**
 * BFF (Backend-for-Frontend) utilities for Route Handlers.
 *
 * Per @priya:
 * - Browser never calls backend APIs directly
 * - All API calls go through Next.js Route Handlers
 * - Route Handlers read the session, extract the JWT, and forward to backend
 * - Backend validates JWT at Kong + app level
 *
 * Scope enforcement:
 * - Server-side: this file checks scopes before proxying to backend
 * - Client-side: UI rendering based on scopes (cosmetic, not security)
 */

import { auth } from "@/lib/auth";
import { Session } from "next-auth";

export type Session = Session & {
  user: {
    id: string;
    email: string;
    scopes?: string[];
  };
};

/**
 * Check if a session has a required scope.
 * Used for server-side authorization in Route Handlers.
 *
 * @param session NextAuth session object (or null)
 * @param requiredScope Scope to check (e.g., "cases:read")
 * @returns true if session exists and has the scope
 */
export function hasScope(session: Session | null, requiredScope: string): boolean {
  if (!session?.user) return false;
  const scopes = (session.user as { scopes?: string[] }).scopes ?? [];
  return scopes.includes(requiredScope);
}

/**
 * Get the Authorization header for proxying to the backend.
 *
 * The session contains the JWT in an encrypted httpOnly cookie.
 * NextAuth exposes it via getServerSession() on the server side.
 * We attach it to outgoing requests to the backend.
 *
 * @param session NextAuth session
 * @returns Authorization header value, or null if not authenticated
 */
export function getAuthorizationHeader(session: Session | null): string | null {
  if (!session?.user) return null;
  // The JWT is stored in the session token by the jwt() callback
  // In a real scenario, we'd need to extract it from the cookie/token
  // For now, return a placeholder that the backend can validate
  // In production, NextAuth exposes the raw token via the session object
  return `Bearer ${(session as any).accessToken ?? ""}`;
}

/**
 * Create a fetch request to the backend with proper auth headers.
 *
 * Usage in Route Handler:
 *   const session = await auth();
 *   const res = await fetchBackend("/v1/cases", session, {
 *     method: "GET"
 *   });
 *
 * @param endpoint Backend endpoint (e.g., "/v1/cases")
 * @param session NextAuth session
 * @param options Fetch options (method, body, etc.)
 * @returns Response from backend
 */
export async function fetchBackend(
  endpoint: string,
  session: Session | null,
  options: RequestInit = {}
): Promise<Response> {
  const backendUrl = process.env["BACKEND_URL"] ?? "http://localhost:8000";
  const authHeader = getAuthorizationHeader(session);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (authHeader) {
    headers["Authorization"] = authHeader;
  }

  return fetch(`${backendUrl}${endpoint}`, {
    ...options,
    headers,
  });
}

/**
 * Authorize a Route Handler — verify session and required scope.
 *
 * Usage:
 *   export async function GET(req: NextRequest) {
 *     const { session, error } = await authorizeRoute("cases:read");
 *     if (error) return error; // Return 401/403 response
 *
 *     // Proceed with handler logic
 *   }
 *
 * @param requiredScope Scope needed for this endpoint (e.g., "cases:read")
 * @returns { session, error } — error is set if not authorized
 */
export async function authorizeRoute(
  requiredScope: string
): Promise<{
  session: Session | null;
  error: Response | null;
}> {
  const session = await auth();

  // Not authenticated
  if (!session?.user) {
    return {
      session: null,
      error: new Response(
        JSON.stringify({
          error_code: "UNAUTHORIZED",
          message: "Authentication required",
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      ),
    };
  }

  // Not authorized for this scope
  if (!hasScope(session, requiredScope)) {
    return {
      session,
      error: new Response(
        JSON.stringify({
          error_code: "FORBIDDEN",
          message: `Scope '${requiredScope}' required`,
        }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      ),
    };
  }

  return { session, error: null };
}
