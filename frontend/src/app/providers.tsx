"use client";

/**
 * Client-side providers wrapper.
 *
 * "use client" rationale: SessionProvider and QueryClientProvider both require
 * React context (which is client-only). This is the ONLY place "use client"
 * appears near the root — everything else is Server Components by default.
 *
 * Extracted from layout.tsx so the root layout remains a Server Component.
 */

import { SessionProvider } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

interface ProvidersProps {
  readonly children: ReactNode;
}

export function Providers({ children }: ProvidersProps): React.JSX.Element {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            /**
             * Case queue: stale after 5s (polling interval).
             * Case detail: stale after 30s.
             * These are overridden per-query where needed.
             */
            staleTime: 5_000,
            retry: (failureCount, error) => {
              /**
               * ISS-002: PgBouncer pool exhaustion can surface as 503s.
               * Retry up to 3 times with exponential backoff for 5xx errors.
               * Never retry 4xx errors — those are client mistakes.
               */
              if (
                error instanceof Error &&
                "status" in error &&
                typeof error.status === "number"
              ) {
                if (error.status >= 400 && error.status < 500) {
                  return false;
                }
              }
              return failureCount < 3;
            },
          },
        },
      }),
  );

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </SessionProvider>
  );
}
