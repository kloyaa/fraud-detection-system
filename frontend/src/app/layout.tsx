/**
 * Root layout -- Server Component.
 *
 * Responsibilities:
 * 1. Self-hosted Inter font via next/font (zero layout shift, CSP compliant)
 * 2. Global CSS import
 * 3. SessionProvider wrapper for NextAuth.js (pushed to a thin Client Component)
 * 4. HTML lang attribute for accessibility
 * 5. Metadata for SEO
 * 6. CSP nonce propagation -- reads the per-request nonce from middleware
 *    and passes it to Next.js via the <head> metadata so all framework-
 *    injected inline scripts include the nonce attribute.
 *
 * This is a Server Component. The SessionProvider is extracted to a separate
 * Client Component (Providers) to keep this layout on the server.
 *
 * Security note (@priya, 2026-03-25):
 * The nonce is read from the `x-nonce` request header set by middleware.ts.
 * Next.js 14 App Router automatically applies this nonce to its own inline
 * scripts (hydration, RSC payload). We also make it available for any
 * custom <Script nonce={nonce}> components via headers().
 */

import type { Metadata } from "next";
import { headers } from "next/headers";
import { Inter } from "next/font/google";
import { Providers } from "@/app/providers";
import "@/app/globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "RAS -- Risk Assessment System",
    template: "%s | RAS",
  },
  description:
    "Fraud analyst case management dashboard for the Risk Assessment System.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  // Read the per-request CSP nonce injected by middleware.ts.
  // In Next.js 14, headers() is synchronous in Server Components.
  // The nonce is passed to Providers so any <Script nonce={nonce}> components
  // within the client tree can reference it. Next.js 14 also reads x-nonce
  // from request headers to automatically nonce its own inline hydration scripts.
  const nonce = headers().get("x-nonce") ?? "";

  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen font-sans">
        <Providers nonce={nonce}>{children}</Providers>
      </body>
    </html>
  );
}
