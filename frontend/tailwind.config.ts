import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // SocialOS Brand
        brand: {
          DEFAULT: "#6C3CE1",
          light: "#A78BFA",
          pale: "#EDE8FF",
          50: "#F5F3FF",
          100: "#EDE9FE",
          200: "#DDD6FE",
          300: "#C4B5FD",
          400: "#A78BFA",
          500: "#8B5CF6",
          600: "#7C3AED",
          700: "#6C3CE1",
          800: "#5B21B6",
          900: "#4C1D95",
        },
        // Dark Theme Backgrounds
        dark: {
          base: "#0F0A1E",
          mid: "#1E1640",
          raised: "#2D235A",
          border: "rgba(255,255,255,0.08)",
        },
        // Status Colors
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#F87171",
        info: "#3B82F6",
        // Content Type Colors
        reel: "#3B82F6",
        carousel: "#10B981",
        graphic: "#A78BFA",
        story: "#F59E0B",
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #6C3CE1, #2D235A)",
        "gradient-dark": "linear-gradient(135deg, #1E1640, #0F0A1E)",
        "gradient-card": "linear-gradient(135deg, rgba(108,60,225,0.3), rgba(45,35,90,0.5))",
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backdropBlur: {
        xs: "2px",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 2s linear infinite",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-in-up": "slideInUp 0.3s ease-out",
        "fade-in": "fadeIn 0.3s ease-out",
        "spin-slow": "spin 3s linear infinite",
        glow: "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        shimmer: {
          "0%": { opacity: "0.6" },
          "50%": { opacity: "1" },
          "100%": { opacity: "0.6" },
        },
        slideInRight: {
          from: { transform: "translateX(100%)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
        slideInUp: {
          from: { transform: "translateY(20px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        glow: {
          from: { boxShadow: "0 0 10px rgba(108,60,225,0.3)" },
          to: { boxShadow: "0 0 30px rgba(108,60,225,0.6)" },
        },
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.4)",
        "glass-sm": "0 4px 16px rgba(0,0,0,0.3)",
        brand: "0 4px 24px rgba(108,60,225,0.4)",
        "brand-lg": "0 8px 48px rgba(108,60,225,0.5)",
        glow: "0 0 30px rgba(108,60,225,0.5)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
