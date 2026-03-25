"use client";

/**
 * Login form — Client Component (leaf).
 *
 * "use client" rationale: uses useState for error state, onSubmit handler,
 * and NextAuth signIn function.
 *
 * Uses React Hook Form + Zod for form validation.
 * Calls NextAuth signIn("credentials") — never handles JWTs directly.
 *
 * Accessibility:
 * - Labels associated with inputs via htmlFor
 * - Error messages linked via aria-describedby
 * - Form has accessible name via aria-labelledby
 * - Submit button has loading state announcement
 *
 * @aisha: data-testid conventions:
 * - login-form, login-email, login-password, login-submit, login-error
 */

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { z } from "zod";

const LoginFormSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof LoginFormSchema>;

export function LoginForm(): React.JSX.Element {
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(LoginFormSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  async function onSubmit(data: LoginFormValues): Promise<void> {
    setServerError(null);
    setIsSubmitting(true);

    try {
      const result = await signIn("credentials", {
        email: data.email,
        password: data.password,
        redirect: false,
      });

      if (result?.error) {
        setServerError("Invalid email or password. Please try again.");
        return;
      }

      if (result?.ok) {
        window.location.href = "/dashboard";
      }
    } catch {
      setServerError("An unexpected error occurred. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      data-testid="login-form"
      aria-labelledby="login-heading"
      onSubmit={(e) => void handleSubmit(onSubmit)(e)}
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      noValidate
    >
      <h2 id="login-heading" className="sr-only">
        Sign in to your account
      </h2>

      {serverError ? (
        <div
          data-testid="login-error"
          role="alert"
          className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {serverError}
        </div>
      ) : null}

      <div className="mb-4">
        <label
          htmlFor="login-email"
          className="mb-1 block text-sm font-medium text-gray-700"
        >
          Email
        </label>
        <input
          id="login-email"
          data-testid="login-email"
          type="email"
          autoComplete="email"
          aria-describedby={errors.email ? "email-error" : undefined}
          aria-invalid={errors.email ? "true" : "false"}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="analyst@ras.dev"
          {...register("email")}
        />
        {errors.email ? (
          <p id="email-error" className="mt-1 text-xs text-red-600" role="alert">
            {errors.email.message}
          </p>
        ) : null}
      </div>

      <div className="mb-6">
        <label
          htmlFor="login-password"
          className="mb-1 block text-sm font-medium text-gray-700"
        >
          Password
        </label>
        <input
          id="login-password"
          data-testid="login-password"
          type="password"
          autoComplete="current-password"
          aria-describedby={errors.password ? "password-error" : undefined}
          aria-invalid={errors.password ? "true" : "false"}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter your password"
          {...register("password")}
        />
        {errors.password ? (
          <p id="password-error" className="mt-1 text-xs text-red-600" role="alert">
            {errors.password.message}
          </p>
        ) : null}
      </div>

      <button
        type="submit"
        data-testid="login-submit"
        disabled={isSubmitting}
        aria-busy={isSubmitting}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? "Signing in..." : "Sign in"}
      </button>

      <p className="mt-4 text-center text-xs text-gray-500">
        Development: analyst@ras.dev / analyst123
      </p>
    </form>
  );
}
