"use client";

/**
 * Client-side providers wrapper.
 *
 * "use client" rationale: SessionProvider and QueryClientProvider both require
 * React context (which is client-only). This is the ONLY place "use client"
 * appears near the root -- everything else is Server Components by default.
 *
 * Extracted from layout.tsx so the root layout remains a Server Component.
 *
 * CSP nonce propagation:
 * The root layout (Server Component) reads the per-request nonce from
 * middleware via headers().get("x-nonce") and passes it here as a prop.
 * We expose it via NonceContext so any client component that renders
 * <Script nonce={nonce}> can access it without prop drilling.
 */

import { SessionProvider } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * React context for the CSP nonce.
 *
 * Default value is empty string -- safe fallback if context is missing.
 * An empty nonce attribute is ignored by the browser, so scripts without
 * a valid nonce will be blocked by CSP as expected.
 */
const NonceContext = createContext<string>("");

/**
 * Hook to access the CSP nonce in client components.
 *
 * Usage:
 *   const nonce = useNonce();
 *   <Script src="/analytics.js" nonce={nonce} />
 */
export function useNonce(): string {
  return useContext(NonceContext);
}

interface ProvidersProps {
  readonly children: ReactNode;
  /** CSP nonce from middleware -- pass to any <Script> tags that need it. */
  readonly nonce: string;
}

export function Providers({ children, nonce }: ProvidersProps): React.JSX.Element {
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
               * Never retry 4xx errors -- those are client mistakes.
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
    <NonceContext.Provider value={nonce}>
      <SessionProvider>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </SessionProvider>
    </NonceContext.Provider>
  );
}
