/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        blue: {
          50: "var(--sw-blue-50)",
          100: "var(--sw-blue-100)",
          200: "var(--sw-blue-200)",
          300: "var(--sw-blue-300)",
          400: "var(--sw-blue-400)",
          500: "var(--sw-blue-500)",
          600: "var(--sw-blue-600)",
          700: "var(--sw-blue-700)",
          800: "var(--sw-blue-800)",
          900: "var(--sw-blue-900)",
        },
        green: {
          50: "var(--sw-green-50)",
          100: "var(--sw-green-100)",
          500: "var(--sw-green-500)",
          600: "var(--sw-green-600)",
          700: "var(--sw-green-700)",
        },
        yellow: {
          50: "var(--sw-yellow-50)",
          100: "var(--sw-yellow-100)",
          200: "var(--sw-yellow-200)",
          400: "var(--sw-yellow-400)",
          500: "var(--sw-yellow-500)",
          800: "var(--sw-yellow-800)",
          900: "var(--sw-yellow-900)",
        },
        ink: {
          50: "var(--sw-ink-50)",
          100: "var(--sw-ink-100)",
          200: "var(--sw-ink-200)",
          300: "var(--sw-ink-300)",
          400: "var(--sw-ink-400)",
          500: "var(--sw-ink-500)",
          600: "var(--sw-ink-600)",
          700: "var(--sw-ink-700)",
          800: "var(--sw-ink-800)",
          900: "var(--sw-ink-900)",
        },
        paper: "var(--sw-paper)",
        brand: "var(--brand)",
      },
      fontFamily: {
        display: "var(--font-display)",
        body: "var(--font-body)",
        mono: "var(--font-mono)",
      },
    },
  },
  plugins: [],
  corePlugins: {
    // The product CSS owns layout/visuals; Tailwind is available for new bits.
    preflight: false,
  },
};
