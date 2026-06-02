/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Marca AIDOC — alineada a CIISA: navy profundo (#012045) dominante.
        brand: {
          50: "#eaeef4",
          100: "#cbd6e6",
          200: "#9ab0cf",
          300: "#6285b0",
          400: "#2f568a",
          500: "#06346b",
          600: "#022a59",
          700: "#012045",
          800: "#01172f",
          900: "#010f20",
          DEFAULT: "#012045",
          dark: "#01172f",
          light: "#eaeef4",
        },
        // Acento CIISA — verde lima, SOLO para detalles puntuales (estados, éxito).
        accent: {
          50: "#f4fce0",
          100: "#e6f8bb",
          200: "#cdee85",
          300: "#b3e34d",
          400: "#9bd71e",
          500: "#92d500",
          600: "#76aa00",
          700: "#5a8000",
          800: "#466100",
          900: "#3a4f08",
          DEFAULT: "#92d500",
        },
        // Neutros cálidos (en vez del gris azulado por defecto)
        surface: {
          0: "#ffffff",
          50: "#fafaf9",
          100: "#f5f5f4",
          200: "#e7e5e4",
          300: "#d6d3d1",
          400: "#a8a29e",
          500: "#78716c",
          600: "#57534e",
          700: "#44403c",
          800: "#292524",
          900: "#1c1917",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.05), 0 4px 12px -2px rgb(0 0 0 / 0.06)",
        pop: "0 10px 38px -10px rgb(0 0 0 / 0.20), 0 0 1px rgb(0 0 0 / 0.10)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.2" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "scale-in": "scale-in 0.15s ease-out",
        blink: "blink 1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
