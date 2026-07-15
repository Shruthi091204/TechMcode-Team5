import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--bg-void)",
        panel: {
          DEFAULT: "var(--bg-panel)",
          raised: "var(--bg-panel-raised)",
        },
        primary: {
          DEFAULT: "var(--red-critical)",
        },
        "border-muted": "var(--line-hairline)",
        "text-muted": "var(--grey-muted)",
        foreground: "var(--white-signal)",
        confirmed: "#3FA796",
        correlated: "#E8A94B",
        missing: "var(--grey-muted)",
        "red-critical": "var(--red-critical)",
        "red-dim": "var(--red-dim)",
        "red-glow": "var(--red-glow)",
        "white-signal": "var(--white-signal)",
        "grey-muted": "var(--grey-muted)",
        "border-hairline": "var(--line-hairline)",
      },
      fontFamily: {
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
      },
      animation: {
        "radar-sweep": "radar-sweep 2s cubic-bezier(0.2, 0.8, 0.2, 1) infinite",
      },
      keyframes: {
        "radar-sweep": {
          "0%": { transform: "scale(1)", opacity: "0.8" },
          "100%": { transform: "scale(2.5)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
