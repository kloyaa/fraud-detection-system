/**
 * Risk level badge component.
 *
 * Renders LOW / MEDIUM / HIGH / CRITICAL with WCAG 2.1 AA compliant colors.
 * Never relies on color alone (WCAG 1.4.1) — text label is always visible.
 *
 * All risk levels include directional indicators:
 * - LOW: downward arrow
 * - MEDIUM: right arrow
 * - HIGH: upward arrow
 * - CRITICAL: double upward arrow
 *
 * Rendering: Server Component (no interactivity, no hooks).
 */

import { cn } from "@/lib/cn";
import type { RiskLevel } from "@/types/ras-api";

interface RiskBadgeProps {
  readonly level: RiskLevel;
  readonly className?: string;
}

const RISK_LEVEL_CONFIG = {
  LOW: {
    label: "LOW",
    indicator: "\u2193", // ↓
    classes:
      "bg-risk-low-bg text-risk-low-text border-risk-low-border",
    srDescription: "Low risk",
  },
  MEDIUM: {
    label: "MEDIUM",
    indicator: "\u2192", // →
    classes:
      "bg-risk-medium-bg text-risk-medium-text border-risk-medium-border",
    srDescription: "Medium risk",
  },
  HIGH: {
    label: "HIGH",
    indicator: "\u2191", // ↑
    classes:
      "bg-risk-high-bg text-risk-high-text border-risk-high-border",
    srDescription: "High risk",
  },
  CRITICAL: {
    label: "CRITICAL",
    indicator: "\u21C8", // ⇈
    classes:
      "bg-risk-critical-bg text-risk-critical-text border-risk-critical-border",
    srDescription: "Critical risk",
  },
} as const satisfies Record<RiskLevel, {
  label: string;
  indicator: string;
  classes: string;
  srDescription: string;
}>;

export function RiskBadge({ level, className }: RiskBadgeProps): React.JSX.Element {
  const config = RISK_LEVEL_CONFIG[level];

  return (
    <span
      data-testid="risk-badge-level"
      role="status"
      aria-label={config.srDescription}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold",
        config.classes,
        className,
      )}
    >
      <span aria-hidden="true">{config.indicator}</span>
      {config.label}
    </span>
  );
}
