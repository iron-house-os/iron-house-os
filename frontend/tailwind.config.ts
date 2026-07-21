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
        brand: {
          gold: "#DDAE58",
          charcoal: "#34373A",
          black: "#0B0D11",
          silver: "#D9DCE0",
        },
        signal: {
          blue: "#2563eb",
          green: "#0f8b62",
          amber: "#b7791f",
          red: "#c2410c",
        },
      },
      boxShadow: {
        brand: "0 18px 50px rgba(11, 13, 17, 0.22)",
      },
    },
  },
  plugins: [],
} satisfies Config;
