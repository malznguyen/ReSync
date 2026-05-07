import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f7f2",
          100: "#ededdf",
          200: "#d7d5c2",
          500: "#686b58",
          700: "#303426",
          900: "#171a12"
        },
        copper: {
          100: "#f5dfd3",
          400: "#c77751",
          600: "#96472c"
        },
        lagoon: {
          100: "#d9f0ee",
          400: "#4aa9a0",
          600: "#1d6d68"
        }
      },
      boxShadow: {
        panel: "0 22px 60px rgba(23, 26, 18, 0.10)",
        control: "0 12px 26px rgba(23, 26, 18, 0.08)"
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "Segoe UI Variable", "Segoe UI", "sans-serif"],
        display: [
          "var(--font-instrument)",
          "Segoe UI Variable",
          "Segoe UI",
          "sans-serif"
        ]
      }
    }
  },
  plugins: []
};

export default config;
