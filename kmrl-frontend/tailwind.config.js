/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        'surface-raised': 'var(--color-surface-raised)',
        border: 'var(--color-border)',
        'border-strong': 'var(--color-border-strong)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        accent: 'var(--color-accent)',
        'accent-bright': 'var(--color-accent-bright)',
        'accent-dim': 'var(--color-accent-dim)',
        'signal-red': 'var(--color-signal-red)',
        'signal-amber': 'var(--color-signal-amber)',
        'signal-green': 'var(--color-signal-green)',
        'signal-blue': 'var(--color-signal-blue)',
      },
      fontFamily: {
        display: ['IBM Plex Serif', 'Georgia', 'serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
