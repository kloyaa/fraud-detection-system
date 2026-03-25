/**
 * NextAuth.js v5 middleware — route protection.
 *
 * Protected routes: /dashboard/**, /admin/**
 * Public routes:    /, /login, /api/auth/**, /api/health
 *
 * Unauthenticated users on protected routes are redirected to /login.
 * Authenticated users visiting /login are redirected to /dashboard.
 *
 * Security note (coordinated with @priya):
 * - Session is stored in an encrypted httpOnly cookie managed by NextAuth.
 * - The middleware verifies the session token on every protected request
 *   at the Edge, before any page component or Route Handler runs.
 */

export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     * - public assets
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
