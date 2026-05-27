import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#121417",
        paper: "#f7f7f2",
        line: "#d7d8ce",
        pitch: "#1f7a4d",
        alert: "#b02a37",
        gold: "#c9972b",
      },
    },
  },
  plugins: [],
};

export default config;

