/**
 * Dashboard shell layout — Server Component.
 *
 * Provides the analyst dashboard navigation chrome:
 * - Top navigation bar with user session info
 * - Sidebar navigation (case queue, admin, models)
 * - Main content area
 *
 * This is a Server Component — no interactivity in the layout shell itself.
 * Interactive elements (user menu dropdown) are extracted to Client Components.
 */

import Link from "next/link";
import type { ReactNode } from "react";

interface DashboardLayoutProps {
  readonly children: ReactNode;
}

export default function DashboardLayout({
  children,
}: DashboardLayoutProps): React.JSX.Element {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Top navigation bar */}
      <header className="border-b border-gray-200 bg-white">
        <nav
          className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4"
          aria-label="Primary navigation"
        >
          <div className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-lg font-bold text-gray-900"
              data-testid="nav-logo"
            >
              RAS
            </Link>

            <div className="hidden items-center gap-4 sm:flex">
              <Link
                href="/dashboard"
                className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
                data-testid="nav-case-queue"
              >
                Case Queue
              </Link>
              <Link
                href="/admin/rules"
                className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
                data-testid="nav-rules"
              >
                Rules
              </Link>
              <Link
                href="/models"
                className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
                data-testid="nav-models"
              >
                Models
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="text-sm text-gray-500"
              data-testid="nav-env-badge"
            >
              {process.env.NEXT_PUBLIC_APP_ENV === "development" ? "DEV" : ""}
            </span>
          </div>
        </nav>
      </header>

      {/* Main content */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-3">
        <p className="text-center text-xs text-gray-400">
          Risk Assessment System v1.0.0
        </p>
      </footer>
    </div>
  );
}
