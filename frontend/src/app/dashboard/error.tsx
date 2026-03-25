"use client";

/**
 * Dashboard error boundary — Client Component.
 *
 * "use client" rationale: Error boundaries must be Client Components
 * (React requirement — error boundaries use componentDidCatch internally).
 *
 * ISS-002: PgBouncer pool exhaustion may surface as 503 errors from the
 * backend. This boundary shows a user-friendly retry prompt instead of
 * a blank screen.
 *
 * Accessibility:
 * - Error message in an alert role for screen readers
 * - Retry button with clear label
 * - Focus moves to the error message on render
 */

import { useEffect, useRef } from "react";

interface DashboardErrorProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

export default function DashboardError({
  error,
  reset,
}: DashboardErrorProps): React.JSX.Element {
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    /** Focus the error container so screen readers announce it */
    errorRef.current?.focus();
  }, []);

  useEffect(() => {
    /** Log error for observability (Sentry integration point) */
    console.error("[DashboardError]", error);
  }, [error]);

  return (
    <div
      ref={errorRef}
      role="alert"
      tabIndex={-1}
      className="flex flex-col items-center justify-center px-4 py-16"
      data-testid="dashboard-error"
    >
      <h2 className="mb-2 text-lg font-semibold text-gray-900">
        Something went wrong
      </h2>
      <p className="mb-6 max-w-md text-center text-sm text-gray-600">
        We could not load the case queue. This may be a temporary issue with the
        backend service. Please try again.
      </p>
      <button
        type="button"
        onClick={reset}
        data-testid="dashboard-error-retry"
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Retry
      </button>
    </div>
  );
}
