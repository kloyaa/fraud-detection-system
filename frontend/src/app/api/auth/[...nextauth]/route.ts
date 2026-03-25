/**
 * NextAuth.js v5 Route Handler.
 *
 * Handles all auth routes:
 * - GET  /api/auth/signin
 * - POST /api/auth/signin
 * - GET  /api/auth/signout
 * - POST /api/auth/signout
 * - GET  /api/auth/session
 * - GET  /api/auth/csrf
 * - GET  /api/auth/providers
 *
 * Security (coordinated with @priya):
 * - Session stored in encrypted httpOnly cookie (not localStorage)
 * - Credentials provider is DEV ONLY
 * - Keycloak OIDC in staging/prod
 */

import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
