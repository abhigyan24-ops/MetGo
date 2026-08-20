/**
 * SignalLight — railway semantic indicator
 * state: 'red' | 'amber' | 'green' | 'blue'
 * size:  'sm' (8px default) | 'md' (11px) | 'lg' (14px)
 * pulse: boolean — continuous glow pulse (for live states)
 */
const SIGNAL_COLORS = {
  red:   { color: 'var(--color-signal-red)',   glow: 'rgba(229, 72, 77, .35)'   },
  amber: { color: 'var(--color-signal-amber)', glow: 'rgba(245, 166, 35, .35)'  },
  green: { color: 'var(--color-signal-green)', glow: 'rgba(61, 214, 140, .35)'  },
  blue:  { color: 'var(--color-signal-blue)',  glow: 'rgba(47, 125, 250, .35)'  },
}
const SIZES = { sm: 8, md: 11, lg: 14 }

export function SignalLight({ state = 'green', size = 'sm', pulse = false, className = '' }) {
  const { color, glow } = SIGNAL_COLORS[state] || SIGNAL_COLORS.green
  const px = SIZES[size] || SIZES.sm

  return (
    <span
      className={`signal-light${pulse ? ' signal-pulse' : ''}${className ? ` ${className}` : ''}`}
      style={{
        display: 'inline-block',
        width: px,
        height: px,
        borderRadius: '50%',
        background: color,
        boxShadow: pulse ? `0 0 0 3px ${glow}` : `0 0 5px ${glow}`,
        flexShrink: 0,
      }}
      aria-hidden="true"
    />
  )
}

/**
 * SignalSweep — animated three-dot sweep used during loading
 * Lights up red → amber → green in sequence, then loops.
 * Used in the What-If panel during solver runs.
 */
export function SignalSweep() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 14px',
        background: 'var(--color-bg)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-card)',
        width: 'fit-content',
      }}
    >
      {['red', 'amber', 'green'].map((state, i) => (
        <span
          key={state}
          style={{
            display: 'inline-block',
            width: 12,
            height: 12,
            borderRadius: '50%',
            background: SIGNAL_COLORS[state].color,
            opacity: 0.25,
            animation: `signalSweep 1.5s ease-in-out ${i * 0.35}s infinite`,
          }}
        />
      ))}
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: 'var(--color-text-muted)',
          letterSpacing: '.08em',
          marginLeft: 6,
        }}
      >
        RE-PLANNING…
      </span>

      <style>{`
        @keyframes signalSweep {
          0%, 100% { opacity: 0.2; transform: scale(1); }
          40%       { opacity: 1;   transform: scale(1.15); }
        }
        @media (prefers-reduced-motion: reduce) {
          @keyframes signalSweep { 0%, 100% { opacity: 0.6; } }
        }
      `}</style>
    </div>
  )
}

/**
 * ConstraintLight — inline signal dot + label for constraint types.
 * hard → red, soft → amber
 */
export function ConstraintLight({ type }) {
  const state = type === 'hard' ? 'red' : type === 'soft' ? 'amber' : 'blue'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <SignalLight state={state} size="sm" />
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '.08em',
          textTransform: 'uppercase',
          color: SIGNAL_COLORS[state].color,
        }}
      >
        {type}
      </span>
    </span>
  )
}
