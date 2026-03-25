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
    jwt({ token, user }) {
      token.role = (user as { role?: string }).role ?? token.role ?? "analyst";
      token.userId = user.id ?? token.userId;
      return token;
    },

    session({ session, token }) {
      session.user.id = token.userId as string;
      (session.user as { role?: string }).role = token.role as string;
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
