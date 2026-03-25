import type { Preview } from "@storybook/react";
import "../src/app/globals.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },

    viewport: {
      defaultViewport: "desktop",
      viewports: {
        desktop: {
          name: "Desktop (1280×800)",
          styles: { width: "1280px", height: "800px" },
          type: "desktop",
        },
        tablet: {
          name: "Tablet (768×1024)",
          styles: { width: "768px", height: "1024px" },
          type: "tablet",
        },
        mobile: {
          name: "Mobile (375×812)",
          styles: { width: "375px", height: "812px" },
          type: "mobile",
        },
      },
    },

    /** axe-core accessibility rules — WCAG 2.1 AA mandatory */
    a11y: {
      config: {
        rules: [
          { id: "color-contrast", enabled: true },
          { id: "label", enabled: true },
          { id: "button-name", enabled: true },
        ],
      },
    },

    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#ffffff" },
        { name: "dark", value: "#0f172a" },
      ],
    },
  },
};

export default preview;
