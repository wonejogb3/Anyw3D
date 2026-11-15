/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#e6edf3",
        muted: "#8b97a6",
        panel: "#171c23",
        panel2: "#1e252e",
        line: "#2a333f",
        accent: "#35d0ba",
        accent2: "#f5a623",
      },
      fontFamily: {
        ui: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
