/**
 * Loading skeleton component.
 *
 * Used during server-side data fetching and cold-start latency (ISS-001).
 * Designed to match the exact dimensions of the content it replaces
 * to prevent Cumulative Layout Shift (CLS target: < 0.1).
 *
 * Rendering: Server Component (pure CSS animation, no JS).
 */

import { cn } from "@/lib/cn";

interface SkeletonProps {
  readonly className?: string;
  /** Accessible label for the loading state */
  readonly label?: string;
}

export function Skeleton({
  className,
  label = "Loading...",
}: SkeletonProps): React.JSX.Element {
  return (
    <div
      data-testid="skeleton-loader"
      role="status"
      aria-label={label}
      className={cn(
        "animate-pulse rounded-md bg-gray-200",
        className,
      )}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pre-built skeleton variants for consistent CLS-free loading states
// ---------------------------------------------------------------------------

/** Skeleton matching the risk badge dimensions */
export function RiskBadgeSkeleton(): React.JSX.Element {
  return <Skeleton className="h-5 w-20" label="Loading risk level" />;
}

/** Skeleton matching a table row */
export function TableRowSkeleton(): React.JSX.Element {
  return (
    <div className="flex items-center gap-4 py-3" role="status" aria-label="Loading table row">
      <Skeleton className="h-4 w-32" label="Loading cell" />
      <Skeleton className="h-4 w-24" label="Loading cell" />
      <Skeleton className="h-5 w-20" label="Loading cell" />
      <Skeleton className="h-5 w-20" label="Loading cell" />
      <Skeleton className="h-4 w-16" label="Loading cell" />
    </div>
  );
}

/** Skeleton for the full case queue table */
export function CaseQueueSkeleton(): React.JSX.Element {
  return (
    <div data-testid="case-queue-skeleton" aria-label="Loading case queue" role="status">
      <span className="sr-only">Loading case queue...</span>
      {Array.from({ length: 8 }, (_, i) => (
        <TableRowSkeleton key={i} />
      ))}
    </div>
  );
}
