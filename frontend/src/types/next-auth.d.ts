/**
 * NextAuth.js v5 module augmentation.
 *
 * Extends the default Session, User, and JWT types to include RAS-specific
 * fields set in the jwt() and session() callbacks in @/lib/auth.ts.
 *
 * Without this file, the base @auth/core types have:
 *   - Session.user?: { id?: string; name?: string | null; email?: string | null; image?: string | null }
 *
 * After augmentation:
 *   - Session.user.id is string (non-optional)
 *   - Session.user.email is string (non-optional)
 *   - Session.user.scopes is string[] (optional)
 *   - Session.accessToken is string (optional, for BFF proxy)
 *
 * Coordinated with @priya: accessToken is only used server-side in Route
 * Handlers for BFF proxy calls. It is NEVER exposed to the browser.
 *
 * @see https://authjs.dev/getting-started/typescript#module-augmentation
 */

import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email: string;
      image?: string | null;
      scopes?: string[];
    };
    accessToken?: string;
  }

  interface User {
    id: string;
    email: string;
    name?: string | null;
    image?: string | null;
    role?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string;
    email?: string | null;
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    scopes?: string[];
    error?: string;
  }
}
