import { motion, AnimatePresence } from 'framer-motion'

/**
 * PAToast — PA-announcement–style notification banner.
 * Styled like a platform departure board announcement.
 * Slides in from top, can be dismissed.
 *
 * Props:
 *  type     — 'error' | 'scenario' | 'info'
 *  show     — boolean
 *  children — banner content
 *  action   — { label, onClick } optional action button
 */
const TYPE_STYLES = {
  error: {
    border: '1px solid rgba(229, 72, 77, .3)',
    background: 'rgba(229, 72, 77, .07)',
    accentColor: 'var(--color-signal-red)',
    prefix: '⚠ SYSTEM',
  },
  scenario: {
    border: '1px solid rgba(47, 125, 250, .3)',
    background: 'rgba(47, 125, 250, .07)',
    accentColor: 'var(--color-accent-bright)',
    prefix: '◈ SCENARIO',
  },
  info: {
    border: '1px solid rgba(61, 214, 140, .3)',
    background: 'rgba(61, 214, 140, .07)',
    accentColor: 'var(--color-signal-green)',
    prefix: '● NOTICE',
  },
}

export function PAToast({ type = 'info', show = true, children, action }) {
  const styles = TYPE_STYLES[type] || TYPE_STYLES.info

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -12, scaleY: 0.9 }}
          animate={{ opacity: 1, y: 0, scaleY: 1 }}
          exit={{ opacity: 0, y: -8, scaleY: 0.95 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          style={{
            marginBottom: 18,
            borderRadius: 10,
            padding: '11px 16px',
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            fontSize: 12,
            border: styles.border,
            background: styles.background,
            transformOrigin: 'top center',
          }}
        >
          {/* PA prefix tag */}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              fontWeight: 800,
              letterSpacing: '.14em',
              color: styles.accentColor,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {styles.prefix}
          </span>

          {/* Content */}
          <div style={{ flex: 1, color: 'var(--color-text-secondary)', fontSize: 12 }}>
            {children}
          </div>

          {/* Optional action */}
          {action && (
            <button
              onClick={action.onClick}
              style={{
                border: 0,
                background: 'transparent',
                fontWeight: 700,
                fontSize: 11,
                color: styles.accentColor,
                cursor: 'pointer',
                textDecoration: 'underline',
                textUnderlineOffset: 2,
                whiteSpace: 'nowrap',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {action.label}
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
