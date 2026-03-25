/**
 * Root layout — Server Component.
 *
 * Responsibilities:
 * 1. Self-hosted Inter font via next/font (zero layout shift, CSP compliant)
 * 2. Global CSS import
 * 3. SessionProvider wrapper for NextAuth.js (pushed to a thin Client Component)
 * 4. HTML lang attribute for accessibility
 * 5. Metadata for SEO
 *
 * This is a Server Component. The SessionProvider is extracted to a separate
 * Client Component (Providers) to keep this layout on the server.
 */

import type { Metadata } from "next";
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
    default: "RAS — Risk Assessment System",
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
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
