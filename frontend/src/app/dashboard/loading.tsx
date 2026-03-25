/**
 * Dashboard loading state — Server Component.
 *
 * Shown during server-side data fetching (Suspense boundary).
 * Uses skeleton components that match the exact dimensions of the
 * CaseQueue table to prevent Cumulative Layout Shift (CLS < 0.1).
 *
 * ISS-001: ML model cold-start latency > 300ms — this skeleton
 * ensures the user sees a stable layout while the backend responds.
 */

import { CaseQueueSkeleton } from "@/components/ui/Skeleton";

export default function DashboardLoading(): React.JSX.Element {
  return (
    <div>
      <div className="mb-6">
        <div className="h-7 w-48 animate-pulse rounded bg-gray-200" />
        <div className="mt-2 h-4 w-80 animate-pulse rounded bg-gray-200" />
      </div>

      <CaseQueueSkeleton />
    </div>
  );
}
