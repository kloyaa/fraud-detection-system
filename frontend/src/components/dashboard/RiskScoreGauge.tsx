"use client";

/**
 * Risk score gauge visualization — Client Component.
 *
 * Uses Recharts (PieChart in gauge mode) to render a semicircular gauge
 * showing the risk score from 0.0 to 1.0.
 *
 * "use client" rationale: Recharts uses DOM measurements and event handlers
 * internally. This is pushed to the leaf — the parent case detail page
 * remains a Server Component.
 *
 * Accessibility:
 * - role="img" with descriptive aria-label containing the full data summary
 * - Never relies on color alone: numeric score + risk level text are always visible
 * - WCAG 1.4.1 compliant: text label supplements the gauge color
 *
 * @aisha: data-testid="risk-score-gauge"
 */

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { RiskBadge } from "@/components/ui/Badge";
import type { RiskLevel } from "@/types/ras-api";

interface RiskScoreGaugeProps {
  /** Risk score in [0.0, 1.0] */
  readonly score: number;
  /** Risk level classification */
  readonly level: RiskLevel;
  /** Optional width override (default: 200) */
  readonly width?: number;
  /** Optional height override (default: 120) */
  readonly height?: number;
}

const GAUGE_COLORS: Record<RiskLevel, string> = {
  LOW: "#166534",       /* green-800 */
  MEDIUM: "#854d0e",    /* yellow-800 */
  HIGH: "#9a3412",      /* orange-800 */
  CRITICAL: "#991b1b",  /* red-800 */
} as const;

const GAUGE_BG = "#e5e7eb"; /* gray-200 — unfilled portion */

export function RiskScoreGauge({
  score,
  level,
  width = 200,
  height = 120,
}: RiskScoreGaugeProps): React.JSX.Element {
  const percentage = Math.round(score * 100);

  /** Gauge data: filled portion + unfilled portion + hidden bottom half */
  const gaugeData = [
    { name: "score", value: score },
    { name: "remaining", value: 1 - score },
  ];

  const ariaLabel = `Risk score: ${score.toFixed(3)} out of 1.0 (${String(percentage)}%). Risk level: ${level}.`;

  return (
    <div
      data-testid="risk-score-gauge"
      role="img"
      aria-label={ariaLabel}
      className="flex flex-col items-center"
    >
      <ResponsiveContainer width={width} height={height}>
        <PieChart>
          <Pie
            data={gaugeData}
            cx="50%"
            cy="100%"
            startAngle={180}
            endAngle={0}
            innerRadius="60%"
            outerRadius="100%"
            dataKey="value"
            stroke="none"
            isAnimationActive={false}
          >
            <Cell fill={GAUGE_COLORS[level]} />
            <Cell fill={GAUGE_BG} />
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      {/* Numeric score — always visible, never color-only */}
      <div className="mt-1 flex flex-col items-center gap-1">
        <span className="text-2xl font-bold tabular-nums text-gray-900">
          {score.toFixed(3)}
        </span>
        <RiskBadge level={level} />
      </div>
    </div>
  );
}
