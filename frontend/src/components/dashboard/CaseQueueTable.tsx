"use client";

/**
 * Interactive case queue table — Client Component.
 *
 * Uses TanStack Table v8 for sorting, filtering, and column management.
 * This is a leaf Client Component — "use client" is pushed to the leaf,
 * not the root.
 *
 * Accessibility:
 * - Native <table> semantics for screen readers
 * - Keyboard-navigable sort controls
 * - aria-sort on sorted columns
 * - Risk/Decision badges use text labels, not color alone
 *
 * @aisha: data-testid conventions:
 * - case-queue-table, case-queue-row, case-queue-header-[column]
 */

import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { RiskBadge } from "@/components/ui/Badge";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import type { RiskScoreResponse } from "@/types/ras-api";

interface CaseQueueTableProps {
  readonly initialData: readonly RiskScoreResponse[];
}

const columnHelper = createColumnHelper<RiskScoreResponse>();

export function CaseQueueTable({
  initialData,
}: CaseQueueTableProps): React.JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "risk_score", desc: true },
  ]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("transaction_id", {
        header: "Transaction ID",
        cell: (info) => (
          <a
            href={`/dashboard/cases/${info.getValue()}`}
            className="font-medium text-blue-700 underline hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
            data-testid="case-queue-cell-transaction"
          >
            {info.getValue()}
          </a>
        ),
      }),
      columnHelper.accessor("risk_score", {
        header: "Risk Score",
        cell: (info) => (
          <span data-testid="case-queue-cell-score" className="font-mono tabular-nums">
            {info.getValue().toFixed(3)}
          </span>
        ),
      }),
      columnHelper.accessor("risk_level", {
        header: "Risk Level",
        cell: (info) => (
          <span data-testid="case-queue-cell-level">
            <RiskBadge level={info.getValue()} />
          </span>
        ),
        filterFn: "equals",
      }),
      columnHelper.accessor("decision", {
        header: "Decision",
        cell: (info) => (
          <span data-testid="case-queue-cell-decision">
            <DecisionBadge decision={info.getValue()} />
          </span>
        ),
        filterFn: "equals",
      }),
      columnHelper.accessor("processing_ms", {
        header: "Latency (ms)",
        cell: (info) => (
          <span className="font-mono tabular-nums text-gray-600">
            {info.getValue()}ms
          </span>
        ),
      }),
      columnHelper.accessor("engine_version", {
        header: "Engine",
        cell: (info) => (
          <span className="text-gray-500">{info.getValue()}</span>
        ),
      }),
    ],
    [],
  );

  const table = useReactTable({
    data: [...initialData],
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table
        data-testid="case-queue-table"
        className="min-w-full divide-y divide-gray-200"
      >
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const sorted = header.column.getIsSorted();
                return (
                  <th
                    key={header.id}
                    data-testid={`case-queue-header-${header.id}`}
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                    aria-sort={
                      sorted === "asc"
                        ? "ascending"
                        : sorted === "desc"
                          ? "descending"
                          : "none"
                    }
                  >
                    {header.isPlaceholder ? null : (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
                        onClick={header.column.getToggleSortingHandler()}
                        aria-label={`Sort by ${String(header.column.columnDef.header ?? "")}`}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        <span aria-hidden="true" className="ml-1">
                          {sorted === "asc"
                            ? "\u2191"
                            : sorted === "desc"
                              ? "\u2193"
                              : "\u2195"}
                        </span>
                      </button>
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-sm text-gray-500"
              >
                No cases in the queue.
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                data-testid="case-queue-row"
                className="transition-colors hover:bg-gray-50"
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="whitespace-nowrap px-4 py-3 text-sm"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
