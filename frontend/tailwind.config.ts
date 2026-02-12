import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        surface: "hsl(var(--surface))",
        "surface-2": "hsl(var(--surface-2))",
        "surface-3": "hsl(var(--surface-3))",
        muted: "hsl(var(--muted))",
        "muted-2": "hsl(var(--muted-2))",
        accent: "hsl(var(--accent))",
        "accent-2": "hsl(var(--accent-2))",
        "accent-3": "hsl(var(--accent-3))",
        ring: "hsl(var(--ring))",
        primary: "#6C63FF",
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 24px 60px -40px rgba(15, 23, 42, 0.45)",
        glow: "0 20px 50px -20px rgba(249, 115, 22, 0.45)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.75s ease both",
        float: "float 10s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
