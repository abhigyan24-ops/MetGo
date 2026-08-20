import { motion } from 'framer-motion'

/**
 * TrainLoader — a small KMRL train icon traveling along a track.
 * Used in:
 *  - The initial loading screen (replaces CSS spinner)
 *  - Any other async-wait state
 *
 * Props:
 *  label  — string shown below the track (optional)
 *  size   — 'sm' | 'md' (default 'md')
 */
export function TrainLoader({ label = '', size = 'md' }) {
  const trackW = size === 'sm' ? 120 : 180
  const trainW = size === 'sm' ? 28  : 38
  const trainH = size === 'sm' ? 14  : 18

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
      }}
    >
      {/* Track + animated train */}
      <div style={{ position: 'relative', width: trackW, height: trainH + 14 }}>
        {/* Rails */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 3,
            background: 'var(--color-border)',
            borderRadius: 99,
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: 6,
            left: 0,
            right: 0,
            height: 3,
            background: 'var(--color-border)',
            borderRadius: 99,
          }}
        />

        {/* Animated train body */}
        <motion.div
          animate={{ x: [0, trackW - trainW, 0] }}
          transition={{
            duration: 2.2,
            ease: 'easeInOut',
            repeat: Infinity,
            repeatType: 'loop',
          }}
          style={{
            position: 'absolute',
            bottom: 8,
            left: 0,
            width: trainW,
            height: trainH,
            borderRadius: `${trainH * 0.5}px ${trainH * 0.3}px ${trainH * 0.2}px ${trainH * 0.2}px`,
            background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-dim))',
            boxShadow: '0 0 12px rgba(47, 125, 250, .45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* Headlight */}
          <div
            style={{
              position: 'absolute',
              right: 3,
              width: 4,
              height: 4,
              borderRadius: '50%',
              background: '#e8f4ff',
              boxShadow: '0 0 6px rgba(200, 230, 255, .9)',
            }}
          />
          {/* KMRL label */}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: size === 'sm' ? 5 : 6,
              fontWeight: 900,
              color: 'rgba(255,255,255,.75)',
              letterSpacing: '.1em',
              userSelect: 'none',
            }}
          >
            KMRL
          </span>
        </motion.div>
      </div>

      {/* Optional label */}
      {label && (
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--color-text-muted)',
            letterSpacing: '.1em',
            textTransform: 'uppercase',
          }}
        >
          {label}
        </span>
      )}
    </div>
  )
}
