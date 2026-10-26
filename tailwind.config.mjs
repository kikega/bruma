/**
 * Sistema de diseño «Bruma Mediterránea».
 * Tailwind v4 lo carga mediante la directiva `@config` de static/src/input.css.
 * @type {import('tailwindcss').Config}
 */
export default {
  content: [
    './templates/**/*.html',
    './core/templates/**/*.html',
    './menu/templates/**/*.html',
    './gallery/templates/**/*.html',
    './reservations/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Fondos
        espuma: '#F8F9FA',
        bruma: {
          DEFAULT: '#E2E8F0',
          50: '#F4F6F9',
          100: '#EDF1F5',
          200: '#E2E8F0',
          300: '#CBD5E1',
        },
        abisal: {
          DEFAULT: '#0F1E2E',
          700: '#16283B',
          800: '#122233',
          900: '#0B1724',
        },
        // Acentos
        mediterraneo: {
          DEFAULT: '#1D4E89',
          light: '#2D64A6',
          dark: '#163C6A',
        },
        salvia: {
          DEFAULT: '#8A9A86',
          light: '#A9B6A5',
          dark: '#6B7A68',
        },
        arena: {
          DEFAULT: '#C2B280',
          light: '#D8CCA6',
          dorada: '#D4AF37',
        },
        tinta: '#1C2A38', // texto principal sobre fondos claros
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', 'ui-serif', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        editorial: '0.28em',
      },
      borderRadius: {
        bruma: '1.25rem',
      },
      boxShadow: {
        bruma: '0 10px 40px -12px rgb(15 30 46 / 0.18)',
        glass: 'inset 0 1px 0 0 rgb(255 255 255 / 0.35), 0 8px 32px -8px rgb(15 30 46 / 0.25)',
      },
      transitionTimingFunction: {
        marea: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      keyframes: {
        'bruma-drift': {
          '0%': { transform: 'translate3d(-6%, 0, 0) scale(1)' },
          '50%': { transform: 'translate3d(4%, -2%, 0) scale(1.08)' },
          '100%': { transform: 'translate3d(-6%, 0, 0) scale(1)' },
        },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translate3d(0, 12px, 0)' },
          to: { opacity: '1', transform: 'translate3d(0, 0, 0)' },
        },
        'scroll-cue': {
          '0%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '50%': { transform: 'translateY(8px)', opacity: '1' },
        },
      },
      animation: {
        'bruma-slow': 'bruma-drift 38s ease-in-out infinite',
        'bruma-fast': 'bruma-drift 26s ease-in-out infinite reverse',
        'fade-in-up': 'fade-in-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) both',
        'scroll-cue': 'scroll-cue 2.4s ease-in-out infinite',
      },
    },
  },
};
