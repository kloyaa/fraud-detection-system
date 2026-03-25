/**
 * Login page — Server Component.
 *
 * Uses NextAuth.js signIn redirect. The actual login form is a thin
 * Client Component (LoginForm) pushed to the leaf.
 *
 * Rendering: Server Component. The form submission triggers NextAuth's
 * server-side credential verification — no client-side JWT handling.
 *
 * Accessibility:
 * - Proper heading hierarchy
 * - Form labels associated with inputs
 * - Error messages linked via aria-describedby
 * - Focus management on error
 */

import type { Metadata } from "next";
import { LoginForm } from "@/app/(auth)/login/LoginForm";

export const metadata: Metadata = {
  title: "Sign In",
};

export default function LoginPage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Risk Assessment System
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to access the analyst dashboard
          </p>
        </div>
        <LoginForm />
      </div>
    </main>
  );
}
