/**
 * Case queue table for the analyst dashboard.
 *
 * Architecture:
 * - CaseQueue (this file) is a SERVER COMPONENT wrapper that fetches initial data.
 * - CaseQueueTable is a CLIENT COMPONENT that provides TanStack Table interactivity
 *   (sorting, filtering, row selection).
 *
 * Rendering strategy: Server Component wrapper + Client Component leaf.
 * This keeps the initial HTML render on the server (fast LCP) while enabling
 * interactive sorting/filtering on the client.
 *
 * @aisha: data-testid attributes follow the convention [component]-[element]:
 * - case-queue-table
 * - case-queue-row
 * - case-queue-cell-transaction
 * - case-queue-cell-score
 * - case-queue-cell-level
 * - case-queue-cell-decision
 */

import { CaseQueueTable } from "@/components/dashboard/CaseQueueTable";
import type { RiskScoreResponse } from "@/types/ras-api";

interface CaseQueueProps {
  /** Pre-fetched cases from the server (passed from page.tsx Server Component) */
  readonly cases: readonly RiskScoreResponse[];
}

export function CaseQueue({ cases }: CaseQueueProps): React.JSX.Element {
  return (
    <section aria-labelledby="case-queue-heading">
      <h2
        id="case-queue-heading"
        className="mb-4 text-lg font-semibold text-gray-900"
      >
        Case Queue
      </h2>
      <CaseQueueTable initialData={cases} />
    </section>
  );
}
