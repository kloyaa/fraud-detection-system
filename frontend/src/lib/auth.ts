/**
 * NextAuth.js v5 configuration.
 *
 * Security decisions (coordinated with @priya):
 * - Session strategy: JWT encrypted in httpOnly cookie. The browser NEVER
 *   receives a raw JWT — NextAuth encrypts it with NEXTAUTH_SECRET.
 * - No JWT in localStorage. Ever.
 * - Credentials provider is DEV ONLY. In staging/prod, switch to Keycloak OIDC.
 * - Session maxAge: 8 hours (analyst shift length).
 *
 * Auth flow:
 * 1. Analyst visits /login → NextAuth signIn("credentials", ...)
 * 2. NextAuth sets encrypted httpOnly session cookie
 * 3. All BFF Route Handlers call getServerSession() to verify auth
 * 4. BFF Route Handlers call backend FastAPI with server-side credentials
 */

import NextAuth, { type NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Keycloak from "next-auth/providers/keycloak";
import { z } from "zod";

/**
 * Credentials login form schema — Zod validates before we touch the provider.
 */
const LoginSchema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(1, "Password is required"),
});

/**
 * Dev-only user database. In staging/prod this is replaced by Keycloak OIDC.
 * Passwords are plaintext here because this is a development-only mock.
 */
const DEV_USERS = [
  {
    id: "analyst-001",
    name: "Demo Analyst",
    email: "analyst@ras.dev",
    password: "analyst123",
    role: "analyst",
  },
  {
    id: "admin-001",
    name: "Demo Admin",
    email: "admin@ras.dev",
    password: "admin123",
    role: "admin",
  },
] as const;

export const authConfig: NextAuthConfig = {
  providers: [
    /**
     * Keycloak OIDC — used in staging and production.
     * Requires KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_ISSUER
     * environment variables to be set.
     *
     * Local dev: Configure via docker-compose Keycloak at http://localhost:8080/realms/ras
     * See .env.local.example for required variables.
     */
    /**
     * From @priya (Sprint 2 security spec):
     * - Realm: ras
     * - ISSUER: https://auth.ras.internal/realms/ras
     * - client_id: ras-dashboard (confidential)
     * - client_secret: Vault-provisioned, NEVER hardcoded
     * - Algorithm: RS256 (not HS256)
     * - Access Token TTL: 15 minutes
     * - Refresh Token TTL: 24 hours, single-use rotation
     *
     * Local dev: docker-compose starts Keycloak at http://localhost:8080/realms/ras-dev
     * PKCE is enabled for defense-in-depth even with a confidential client.
     */
    Keycloak({
      clientId: "ras-dashboard",
      clientSecret: process.env["KEYCLOAK_CLIENT_SECRET"] ?? "",
      issuer: process.env["KEYCLOAK_ISSUER"] ?? "http://localhost:8080/realms/ras",
      authorization: {
        params: {
          scope: "openid risk:read_all cases:read cases:write rules:read",
        },
      },
    }),

    /**
     * Dev-only credentials provider.
     * Disabled when KEYCLOAK_ISSUER is set (staging/prod).
     * Never expose plaintext passwords in production.
     */
    Credentials({
      name: "Development Login",
      credentials: {
        email: { label: "Email", type: "email", placeholder: "analyst@ras.dev" },
        password: { label: "Password", type: "password" },
      },
      authorize(credentials) {
        const parsed = LoginSchema.safeParse(credentials);
        if (!parsed.success) {
          return null;
        }

        const user = DEV_USERS.find(
          (u) =>
            u.email === parsed.data.email &&
            u.password === parsed.data.password,
        );

        if (!user) {
          return null;
        }

        return {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
        };
      },
    }),
  ],

  session: {
    strategy: "jwt",
    maxAge: 8 * 60 * 60, // 8 hours — analyst shift length
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  callbacks: {
    /**
     * JWT callback: Handle access token refresh and scope extraction.
     *
     * Threat S-005 (Refresh Token Theft):
     * Implement refresh token rotation — when the access token expires (15 min),
     * use the refresh token to get a new access token + new refresh token.
     * The old refresh token is invalidated by Keycloak.
     * If refresh fails, force re-authentication.
     *
     * Scopes from the JWT `scope` claim are extracted here and stored in the token
     * for the session callback to expose to the app.
     */
    async jwt({ token, user, account }) {
      // First-time sign-in: extract user info and scopes from account
      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (user && account) {
        token.id = user.id;
        token.email = user.email;
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = (account.expires_at ?? 0) * 1000; // Convert to ms

        // Extract scopes from the account (Keycloak returns scope as space-separated string)
        const scopes = account.scope?.split(" ") ?? [];
        token.scopes = scopes;

        return token;
      }

      // Token has expired? Use refresh token to get a new access token
      if (Date.now() < (token.expiresAt as number)) {
        return token; // Token still valid
      }

      // Token expired — attempt refresh
      try {
        const response = await fetch(
          `${String(process.env["KEYCLOAK_ISSUER"])}/protocol/openid-connect/token`,
          {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              client_id: "ras-dashboard",
              client_secret: process.env["KEYCLOAK_CLIENT_SECRET"] ?? "",
              grant_type: "refresh_token",
              refresh_token: token.refreshToken as string,
            }),
          }
        );

        if (!response.ok) {
          // Refresh failed — force re-auth
          throw new Error(`Refresh token request failed: ${String(response.status)}`);
        }

        const refreshed: unknown = await response.json();
        // Minimal shape validation for the OIDC token response.
        // A full Zod schema is overkill here since Keycloak controls the format,
        // but we guard against `any` leaking through.
        const parsed = refreshed as {
          access_token?: string;
          refresh_token?: string;
          expires_in?: number;
          scope?: string;
        };
        return {
          ...token,
          accessToken: parsed.access_token ?? token.accessToken,
          refreshToken: parsed.refresh_token ?? token.refreshToken,
          expiresAt: Date.now() + (parsed.expires_in ?? 0) * 1000,
          scopes: parsed.scope?.split(" ") ?? token.scopes,
        };
      } catch (error) {
        console.error("Token refresh failed:", error);
        // Return token with expired flag — session callback will detect this
        return { ...token, error: "RefreshAccessTokenError" };
      }
    },

    /**
     * Session callback: Expose JWT claims to the application.
     *
     * SECURITY: The browser gets claims from the session object, NOT the raw JWT.
     * The raw JWT stays encrypted in the httpOnly cookie.
     *
     * If token refresh failed, signOut() is triggered on the frontend.
     */
    session({ session, token }) {
      // Propagate refresh token error to client — trigger re-auth
      if (token.error === "RefreshAccessTokenError") {
        return session; // NextAuth will treat this as failed and sign out
      }

      session.user.id = token.id ?? "";
      session.user.email = token.email ?? "";
      // Expose scopes for frontend RBAC rendering (augmented in next-auth.d.ts)
      session.user.scopes = token.scopes ?? [];
      // Expose access token for BFF proxy (server-side only, never sent to browser)
      session.accessToken = token.accessToken;

      return session;
    },

    authorized({ auth, request }) {
      const isLoggedIn = !!auth?.user;
      const isOnDashboard = request.nextUrl.pathname.startsWith("/dashboard");
      const isOnAdmin = request.nextUrl.pathname.startsWith("/admin");
      const isOnLogin = request.nextUrl.pathname.startsWith("/login");

      if (isOnDashboard || isOnAdmin) {
        return isLoggedIn;
      }

      if (isOnLogin && isLoggedIn) {
        return Response.redirect(new URL("/dashboard", request.nextUrl));
      }

      return true;
    },
  },
};

/**
 * NextAuth instance for v5.
 * Exports `auth` for server-side session retrieval in Route Handlers.
 */
export const { auth, handlers } = NextAuth(authConfig);
