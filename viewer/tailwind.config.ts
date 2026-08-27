import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#FAFAF9",
        panel: "#FFFFFF",
        ink: "#1E293B",
        muted: "#64748B",
        faint: "#94A3B8",
        accent: "#4664e0",
        "accent-soft": "#EEF1FC",
        pos: "#15803D",
        "pos-soft": "#F0FDF4",
        neg: "#DC2626",
        "neg-soft": "#FEF2F2",
        warn: "#B45309",
        "warn-soft": "#FFFBEB",
        line: "#E5E7EB",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        micro: ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.02em" }],
      },
    },
  },
  plugins: [],
};

export default config;
