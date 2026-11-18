/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        nexora: {
          bg: "#080D18",
          secondary: "#101827",
          surface: "#141F31",
          accent: "#648BFF",
          purple: "#8B7CFF",
          success: "#20C997",
          warning: "#F4B740",
          danger: "#F06464",
          text: "#F5F7FC",
          muted: "#94A3B8",
        },
      },
    },
  },
  plugins: [],
};
