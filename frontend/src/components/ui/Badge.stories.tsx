import type { Meta, StoryObj } from "@storybook/react";
import { RiskBadge } from "./Badge";

/**
 * RiskBadge renders a risk level label with WCAG 2.1 AA compliant colors.
 * Never relies on color alone — each level has a directional text indicator.
 */
const meta = {
  title: "UI/RiskBadge",
  component: RiskBadge,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    a11y: { disable: false },
  },
} satisfies Meta<typeof RiskBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Low: Story = {
  args: { level: "LOW" },
};

export const Medium: Story = {
  args: { level: "MEDIUM" },
};

export const High: Story = {
  args: { level: "HIGH" },
};

export const Critical: Story = {
  args: { level: "CRITICAL" },
};

export const AllLevels: Story = {
  args: { level: "LOW" },
  render: () => (
    <div className="flex flex-wrap gap-3">
      <RiskBadge level="LOW" />
      <RiskBadge level="MEDIUM" />
      <RiskBadge level="HIGH" />
      <RiskBadge level="CRITICAL" />
    </div>
  ),
};
