/**
 * Decision badge component.
 *
 * Renders APPROVE / REVIEW / DECLINE with WCAG 2.1 AA compliant colors.
 * Never relies on color alone — text label + icon indicator always visible.
 *
 * Rendering: Server Component (no interactivity, no hooks).
 */

import { cn } from "@/lib/cn";
import type { Decision } from "@/types/ras-api";

interface DecisionBadgeProps {
  readonly decision: Decision;
  readonly className?: string;
}

const DECISION_CONFIG = {
  APPROVE: {
    label: "APPROVE",
    indicator: "\u2713", // ✓
    classes:
      "bg-decision-approve-bg text-decision-approve-text border-decision-approve-border",
    srDescription: "Decision: Approve",
  },
  REVIEW: {
    label: "REVIEW",
    indicator: "\u26A0", // ⚠
    classes:
      "bg-decision-review-bg text-decision-review-text border-decision-review-border",
    srDescription: "Decision: Review",
  },
  DECLINE: {
    label: "DECLINE",
    indicator: "\u2717", // ✗
    classes:
      "bg-decision-decline-bg text-decision-decline-text border-decision-decline-border",
    srDescription: "Decision: Decline",
  },
} as const satisfies Record<Decision, {
  label: string;
  indicator: string;
  classes: string;
  srDescription: string;
}>;

export function DecisionBadge({
  decision,
  className,
}: DecisionBadgeProps): React.JSX.Element {
  const config = DECISION_CONFIG[decision];

  return (
    <span
      data-testid="decision-badge-action"
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
