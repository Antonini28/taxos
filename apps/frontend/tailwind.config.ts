import type { Config } from "tailwindcss";

/**
 * Meridian design system (docs/frontend/01-design-system.md).
 *
 * Every colour is a CSS variable so light and dark are two *selected* designs rather
 * than one inverted: the dark values are tuned for the dark surface, not computed.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "var(--bg-page)",
        surface: "var(--bg-surface)",
        "surface-2": "var(--bg-surface-2)",
        overlay: "var(--bg-overlay)",
        ink: {
          DEFAULT: "var(--ink-primary)",
          secondary: "var(--ink-secondary)",
          muted: "var(--ink-muted)",
        },
        hairline: "var(--border-hairline)",
        strong: "var(--border-strong)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          subtle: "var(--accent-subtle)",
        },
        status: {
          good: "var(--status-good)",
          warning: "var(--status-warning)",
          serious: "var(--status-serious)",
          critical: "var(--status-critical)",
        },
        // CVD-validated categorical series (dataviz standard, doc 01 §1.4)
        series: {
          1: "var(--series-1)",
          2: "var(--series-2)",
          3: "var(--series-3)",
          4: "var(--series-4)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        micro: ["11px", { lineHeight: "16px", letterSpacing: "0.02em" }],
        small: ["13px", { lineHeight: "18px" }],
        body: ["14px", { lineHeight: "20px" }],
        heading: ["16px", { lineHeight: "24px" }],
        title: ["20px", { lineHeight: "28px" }],
        display: ["28px", { lineHeight: "36px" }],
        hero: ["32px", { lineHeight: "38px" }],
      },
      borderRadius: { sm: "4px", md: "6px", lg: "10px" },
      boxShadow: {
        e1: "0 1px 2px rgba(0,0,0,.06)",
        e2: "0 4px 16px rgba(0,0,0,.10)",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 120ms ease-out",
        "slide-in": "slide-in 160ms cubic-bezier(.32,.72,.24,1)",
      },
    },
  },
  plugins: [],
};

export default config;
