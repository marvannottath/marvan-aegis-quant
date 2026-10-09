/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/context/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Institutional Light Design Tokens
        canvas: '#F8FAFC',        // Slate-50: Main application canvas
        panel: '#FFFFFF',         // Crisp pure white cards/panels
        'panel-hover': '#F1F5F9', // Slate-100: Hover surface
        line: '#E2E8F0',          // Slate-200: Subtle divider/border
        'line-strong': '#CBD5E1',  // Slate-300: Active or prominent border
        
        // Typography
        txt: {
          primary: '#0F172A',     // Slate-900: High-contrast primary headers & values
          secondary: '#334155',   // Slate-700: Body & labels
          muted: '#64748B',       // Slate-500: Secondary descriptions
          subtle: '#94A3B8',      // Slate-400: Micro copy & metadata
        },

        // Financial Semantics
        brand: {
          DEFAULT: '#2563EB',     // Blue-600
          hover: '#1D4ED8',       // Blue-700
          subtle: '#EFF6FF',      // Blue-50
        },
        profit: {
          DEFAULT: '#16A34A',     // Green-600
          subtle: '#F0FDF4',      // Green-50
          dark: '#15803D',        // Green-700
        },
        loss: {
          DEFAULT: '#DC2626',     // Red-600
          subtle: '#FEF2F2',      // Red-50
          dark: '#B91C1C',        // Red-700
        },
        warn: {
          DEFAULT: '#D97706',     // Amber-600
          subtle: '#FFFBEB',      // Amber-50
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
};
