import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        iron: {
          50: "#f7f8f8",
          100: "#e6e9ea",
          500: "#647071",
          800: "#253033",
          950: "#111719",
        },
        signal: {
          blue: "#2563eb",
          green: "#0f8b62",
          amber: "#b7791f",
          red: "#c2410c",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
