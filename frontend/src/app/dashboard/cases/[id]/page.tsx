/**
 * Case detail page — Server Component.
 *
 * Rendering strategy: SERVER COMPONENT.
 * Rationale: Case detail data is fetched server-side for fast initial load.
 * The RiskScoreGauge is a Client Component (leaf) for chart interactivity.
 *
 * The page fetches case data server-side and passes it as props to child
 * components. Interactive mutation actions (approve, escalate) will be
 * added in a future sprint as Client Components at /dashboard/cases/[id]/actions.
 *
 * Accessibility:
 * - Proper heading hierarchy (h1 for case ID, h2 for sections)
 * - Data is presented in definition lists for screen reader semantics
 * - RiskScoreGauge has role="img" with full data summary in aria-label
 */

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { RiskScoreGauge } from "@/components/dashboard/RiskScoreGauge";
import { RiskBadge } from "@/components/ui/Badge";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import type { RiskScoreResponse } from "@/types/ras-api";

interface CaseDetailPageProps {
  readonly params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: CaseDetailPageProps): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Case ${id}`,
  };
}

/**
 * Fetch a single case by transaction ID.
 *
 * In this scaffold, returns mock data keyed by ID.
 * Once @sofia's case detail endpoint exists, this will call the BFF server-side.
 */
function getCase(id: string): RiskScoreResponse | null {
  /**
   * TODO(@elena): Replace with server-side fetch to BFF once case detail
   * endpoint exists. For now, return mock data for known IDs.
   */
  const mockCases: Record<string, RiskScoreResponse> = {
    txn_abc123: {
      request_id: "req-001",
      transaction_id: "txn_abc123",
      risk_score: 0.92,
      risk_level: "CRITICAL",
      decision: "DECLINE",
      reason_codes: ["VELOCITY_SPIKE", "NEW_DEVICE"],
      processing_ms: 45,
      engine_version: "1.0.0",
    },
    txn_def456: {
      request_id: "req-002",
      transaction_id: "txn_def456",
      risk_score: 0.67,
      risk_level: "HIGH",
      decision: "REVIEW",
      reason_codes: ["UNUSUAL_AMOUNT"],
      processing_ms: 38,
      engine_version: "1.0.0",
    },
    txn_ghi789: {
      request_id: "req-003",
      transaction_id: "txn_ghi789",
      risk_score: 0.34,
      risk_level: "MEDIUM",
      decision: "REVIEW",
      reason_codes: ["GEO_MISMATCH"],
      processing_ms: 52,
      engine_version: "1.0.0",
    },
    txn_jkl012: {
      request_id: "req-004",
      transaction_id: "txn_jkl012",
      risk_score: 0.08,
      risk_level: "LOW",
      decision: "APPROVE",
      reason_codes: [],
      processing_ms: 31,
      engine_version: "1.0.0",
    },
    txn_mno345: {
      request_id: "req-005",
      transaction_id: "txn_mno345",
      risk_score: 0.85,
      risk_level: "CRITICAL",
      decision: "DECLINE",
      reason_codes: ["VELOCITY_SPIKE", "COMPROMISED_CARD_BIN"],
      processing_ms: 67,
      engine_version: "1.0.0",
    },
  };

  return mockCases[id] ?? null;
}

export default async function CaseDetailPage({
  params,
}: CaseDetailPageProps): Promise<React.JSX.Element> {
  const { id } = await params;
  const caseData = getCase(id);

  if (!caseData) {
    notFound();
  }

  return (
    <div data-testid="case-detail-page">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">
          Case: {caseData.transaction_id}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Request ID: {caseData.request_id}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Risk score gauge */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm lg:col-span-1">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Risk Assessment
          </h2>
          <div className="flex justify-center">
            <RiskScoreGauge score={caseData.risk_score} level={caseData.risk_level} />
          </div>
        </div>

        {/* Case details */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Assessment Details
          </h2>
          <dl className="grid gap-4 sm:grid-cols-2" data-testid="case-detail-fields">
            <div>
              <dt className="text-sm font-medium text-gray-500">Risk Level</dt>
              <dd className="mt-1">
                <RiskBadge level={caseData.risk_level} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Decision</dt>
              <dd className="mt-1">
                <DecisionBadge decision={caseData.decision} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">
                Processing Time
              </dt>
              <dd className="mt-1 font-mono text-sm tabular-nums text-gray-900">
                {caseData.processing_ms}ms
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">
                Engine Version
              </dt>
              <dd className="mt-1 text-sm text-gray-900">
                {caseData.engine_version}
              </dd>
            </div>
          </dl>
        </div>

        {/* Reason codes */}
        {caseData.reason_codes.length > 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm lg:col-span-3">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
              Reason Codes
            </h2>
            <ul
              className="flex flex-wrap gap-2"
              data-testid="case-detail-reason-codes"
              aria-label="FCRA reason codes for this assessment"
            >
              {caseData.reason_codes.map((code) => (
                <li
                  key={code}
                  className="rounded-md border border-gray-300 bg-gray-50 px-3 py-1 text-sm font-mono text-gray-700"
                >
                  {code}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
