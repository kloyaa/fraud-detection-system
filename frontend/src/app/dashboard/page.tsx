/**
 * Dashboard home — Server Component.
 *
 * Rendering strategy: SERVER COMPONENT.
 * Rationale: Initial case queue data is fetched server-side for fast LCP.
 * The CaseQueue component renders the initial HTML on the server.
 * Interactive sorting/filtering is handled by the CaseQueueTable Client Component (leaf).
 *
 * Data flow:
 * 1. This page fetches case data from the BFF (server-side, no browser request)
 * 2. Data is passed as props to CaseQueue (Server Component wrapper)
 * 3. CaseQueue passes data to CaseQueueTable (Client Component leaf)
 *
 * ISS-001 note: If the backend cold-starts (> 300ms), the loading.tsx
 * Suspense boundary shows a skeleton that matches the table dimensions
 * to prevent CLS.
 *
 * ISS-002 note: If PgBouncer pool exhaustion causes a 503, the error.tsx
 * boundary shows a retry prompt.
 */

import type { Metadata } from "next";
import { CaseQueue } from "@/components/dashboard/CaseQueue";
import type { RiskScoreResponse } from "@/types/ras-api";

export const metadata: Metadata = {
  title: "Case Queue",
};

/**
 * Fetch recent cases from the BFF.
 *
 * In this scaffold, we return mock data. Once @sofia's case list endpoint
 * is available, this will call the BFF Route Handler server-side.
 */
function getCases(): RiskScoreResponse[] {
  /**
   * TODO(@elena): Replace with server-side fetch to BFF once case list
   * endpoint exists. For now, return representative mock data so the
   * UI can be developed and tested.
   *
   * Future implementation:
   *   const backendUrl = process.env.BACKEND_URL;
   *   const res = await fetch(`${backendUrl}/v1/cases`, {
   *     cache: "no-store",
   *     headers: { "Content-Type": "application/json" },
   *   });
   *   return RiskScoreResponseArraySchema.parse(await res.json());
   */
  const mockCases: RiskScoreResponse[] = [
    {
      request_id: "req-001",
      transaction_id: "txn_abc123",
      risk_score: 0.92,
      risk_level: "CRITICAL",
      decision: "DECLINE",
      reason_codes: ["VELOCITY_SPIKE", "NEW_DEVICE"],
      processing_ms: 45,
      engine_version: "1.0.0",
    },
    {
      request_id: "req-002",
      transaction_id: "txn_def456",
      risk_score: 0.67,
      risk_level: "HIGH",
      decision: "REVIEW",
      reason_codes: ["UNUSUAL_AMOUNT"],
      processing_ms: 38,
      engine_version: "1.0.0",
    },
    {
      request_id: "req-003",
      transaction_id: "txn_ghi789",
      risk_score: 0.34,
      risk_level: "MEDIUM",
      decision: "REVIEW",
      reason_codes: ["GEO_MISMATCH"],
      processing_ms: 52,
      engine_version: "1.0.0",
    },
    {
      request_id: "req-004",
      transaction_id: "txn_jkl012",
      risk_score: 0.08,
      risk_level: "LOW",
      decision: "APPROVE",
      reason_codes: [],
      processing_ms: 31,
      engine_version: "1.0.0",
    },
    {
      request_id: "req-005",
      transaction_id: "txn_mno345",
      risk_score: 0.85,
      risk_level: "CRITICAL",
      decision: "DECLINE",
      reason_codes: ["VELOCITY_SPIKE", "COMPROMISED_CARD_BIN"],
      processing_ms: 67,
      engine_version: "1.0.0",
    },
  ];

  return mockCases;
}

export default function DashboardPage(): React.JSX.Element {
  const cases = getCases();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Analyst Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review and manage flagged transactions. Sorted by risk score (highest first).
        </p>
      </div>

      <CaseQueue cases={cases} />
    </div>
  );
}
