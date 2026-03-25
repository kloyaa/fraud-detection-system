import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Risk level palette — WCAG 2.1 AA 4.5:1 contrast on white backgrounds */
        risk: {
          low: {
            bg: "#dcfce7",       /* green-100 */
            text: "#166534",     /* green-800 — 7.1:1 on green-100 */
            border: "#86efac",   /* green-300 */
          },
          medium: {
            bg: "#fef9c3",       /* yellow-100 */
            text: "#854d0e",     /* yellow-800 — 5.8:1 on yellow-100 */
            border: "#fde047",   /* yellow-300 */
          },
          high: {
            bg: "#ffedd5",       /* orange-100 */
            text: "#9a3412",     /* orange-800 — 5.5:1 on orange-100 */
            border: "#fdba74",   /* orange-300 */
          },
          critical: {
            bg: "#fee2e2",       /* red-100 */
            text: "#991b1b",     /* red-800 — 6.8:1 on red-100 */
            border: "#fca5a5",   /* red-300 */
          },
        },
        /* Decision palette — WCAG 2.1 AA compliant */
        decision: {
          approve: {
            bg: "#dcfce7",
            text: "#166534",
            border: "#86efac",
          },
          review: {
            bg: "#ffedd5",
            text: "#9a3412",
            border: "#fdba74",
          },
          decline: {
            bg: "#fee2e2",
            text: "#991b1b",
            border: "#fca5a5",
          },
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
