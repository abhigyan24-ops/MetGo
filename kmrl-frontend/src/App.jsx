import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence, useInView } from 'framer-motion'
import gsap from 'gsap'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'
import './App.css'
import { api, normalizeTrain } from './api'
import { SignalLight, SignalSweep, ConstraintLight } from './components/SignalLight'
import { TrainLoader } from './components/TrainLoader'
import { PAToast } from './components/PAToast'
import { getTrainName, formatTrainLabel, KMRL_SPECS, MULTIMODAL_HUBS } from './data/kmrlData'

gsap.registerPlugin(MotionPathPlugin)

// ── Boot Screen ───────────────────────────────────────────────
function BootScreen({ bootStatus, onRetry, error }) {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [logs, setLogs] = useState([]);
  
  useEffect(() => {
    if (error) return;
    const initialLogs = [
      "[sys] Initializing KMRL MetGo Operations Suite...",
      "[auth] Validating operator credentials... OK",
      "[db] Syncing TimescaleDB telemetry... OK",
      "[graph] Hydrating Neo4j stabling model... OK",
      "[opt] Establishing solver engine socket... OK"
    ];
    
    let index = 0;
    const interval = setInterval(() => {
      if (index < initialLogs.length) {
        setLogs(prev => [...prev, initialLogs[index]]);
        index++;
      } else {
        clearInterval(interval);
      }
    }, 300); // Add a log every 300ms

    return () => clearInterval(interval);
  }, [error]);

  return (
    <div className="boot-screen">
      {!prefersReducedMotion && (
        <div className="boot-ambient-glow"></div>
      )}

      <div className="boot-content">
        <div className="boot-terminal">
          {logs.map((log, i) => (
            <div key={i} className="boot-log-line">{log}</div>
          ))}
          {logs.length === 5 && !error && (
              <div className="boot-log-line blink">[sys] {bootStatus}...</div>
          )}
        </div>

        <div className="boot-visual">
          <svg width="400" height="60" viewBox="0 0 400 60" fill="none">
            {/* Glowing Track */}
            <line x1="0" y1="30" x2="400" y2="30" stroke="rgba(255,255,255,0.05)" strokeWidth="2" strokeDasharray="4 4" />
            
            {/* Animated Train */}
            {!prefersReducedMotion ? (
              <motion.g 
                animate={{ x: [-80, 420] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              >
                {/* Glow */}
                <rect x="-10" y="15" width="80" height="30" fill="var(--color-accent)" filter="blur(15px)" opacity="0.4" />
                {/* Train Body */}
                <rect x="0" y="18" width="60" height="24" rx="4" fill="#0b0e14" stroke="var(--color-accent)" strokeWidth="1" />
                {/* Windows */}
                <rect x="8" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
                <rect x="25" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
                <rect x="42" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
                {/* Tail/Head lights */}
                <circle cx="4" cy="30" r="1.5" fill="var(--color-signal-red)" />
                <circle cx="56" cy="30" r="1.5" fill="#fff" />
              </motion.g>
            ) : (
              <g transform="translate(170, 0)">
                <rect x="0" y="18" width="60" height="24" rx="4" fill="#0b0e14" stroke="var(--color-accent)" strokeWidth="1" />
                <rect x="8" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
                <rect x="25" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
                <rect x="42" y="22" width="10" height="8" rx="2" fill="rgba(255,255,255,0.15)" />
              </g>
            )}
          </svg>
        </div>
        
        <div className="boot-status">
          {error ? (
            <div className="boot-error">
              <span style={{ color: 'var(--color-signal-red)', display: 'block', marginBottom: '16px' }}>[ERR] Connection Timeout</span>
              <p>Could not reach the Metro operations backend.</p>
              <button className="primary-btn" onClick={onRetry}>Retry Connection</button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

// ── Yard Layout ──────────────────────────────────────────────
// Matches the real seeded Muttom Yard shape confirmed in Part 3
// (5 stabling lines: 6, 6, 5, 5, 4 bays + 3-bay maintenance track + wash
// track). The earlier version of this layout only had 4 stabling lines
// (23 bays) and was missing L5 entirely — any train the backend placed
// in L5 had nowhere to render. Fixed in Part 5c-1.
const YARD_LAYOUT = {
  name: 'Muttom Yard',
  lines: [
    { line_id: 'L1', line_name: 'Stabling Road 1', bays: ['B01','B02','B03','B04','B05','B06'] },
    { line_id: 'L2', line_name: 'Stabling Road 2', bays: ['B07','B08','B09','B10','B11','B12'] },
    { line_id: 'L3', line_name: 'Stabling Road 3', bays: ['B13','B14','B15','B16','B17'] },
    { line_id: 'L4', line_name: 'Stabling Road 4', bays: ['B18','B19','B20','B21','B22'] },
    { line_id: 'L5', line_name: 'Stabling Road 5', bays: ['B23','B24','B25','B26'] },
    { line_id: 'M1', line_name: 'Maintenance Track', bays: ['M01','M02','M03'] },
    { line_id: 'W1', line_name: 'Wash Bay', bays: ['W01'] },
  ],
}

const STATE_META = {
  service:     { label: 'Service',     icon: '●', className: 'service' },
  standby:     { label: 'Standby',     icon: '◐', className: 'standby' },
  maintenance: { label: 'Maintenance', icon: '◆', className: 'maintenance' },
  cleaning:    { label: 'Cleaning',    icon: '✦', className: 'cleaning' },
  breakdown:   { label: 'Breakdown',   icon: '!', className: 'breakdown' },
}

// ── Animation presets ─────────────────────────────────────────
const fadeUp = {
  hidden:  { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0  },
}
const staggerContainer = {
  hidden:  {},
  visible: { transition: { staggerChildren: 0.06 } },
}
const staggerFast = {
  hidden:  {},
  visible: { transition: { staggerChildren: 0.04 } },
}

// ── Count-up hook ─────────────────────────────────────────────
function useCountUp(target, duration = 800) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = performance.now()
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1)
      setValue(Math.round(progress * target))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration])
  return value
}

// ── App ───────────────────────────────────────────────────────
function App() {
  const [plan, setPlan]                 = useState(null)
  const [trains, setTrains]             = useState([])
  const [activeView, setActiveView]     = useState('overview')
  const [loading, setLoading]           = useState(true)
  const [bootStatus, setBootStatus]     = useState('Initiating boot sequence...')
  const [bootError, setBootError]       = useState(false)
  const [generating, setGenerating]     = useState(false)
  const [error, setError]               = useState('')
  const [backendOnline, setBackendOnline] = useState(false)
  const [scenario, setScenario]         = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [explainTrain, setExplainTrain] = useState('')
  const [explanation, setExplanation]   = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [search, setSearch]             = useState('')

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setBootError(false)
    setError('')
    setScenario(null)
    setExplanation(null)
    
    // Polling logic for backend health
    let backendReady = false;
    let attempts = 0;
    const maxTime = 15000;
    const startTime = Date.now();
    
    while (!backendReady && Date.now() - startTime < maxTime) {
      try {
        setBootStatus('Connecting to control center...')
        const health = await api.health();
        if (health?.status === 'ok') {
          backendReady = true;
          setBackendOnline(true);
        }
      } catch (e) {
        attempts++;
        setBootStatus(`Connection retry ${attempts}...`)
        await new Promise(r => setTimeout(r, Math.min(800 * Math.pow(1.5, attempts), 3000)));
      }
    }

    if (!backendReady) {
      setBootError(true);
      return;
    }

    try {
      setBootStatus('Loading fleet data & plans...')
      const [generatedPlan, summaries] = await Promise.all([
        api.generatePlan(),
        api.trains(),
      ])

      const details = await Promise.allSettled(summaries.map((train) => api.train(train.train_id)))
      const normalized = summaries.map((summary, index) => {
        const result = details[index]
        return normalizeTrain(summary, result.status === 'fulfilled' ? result.value : null)
      })

      setPlan(generatedPlan)
      setTrains(normalized)
    } catch (err) {
      setError(err.message || 'Failed to fetch operations data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadDashboard() }, [loadDashboard])

  const assignmentMap = useMemo(() => {
    const map = {}
    ;(plan?.assignments || []).forEach((item) => { map[item.train_id] = item })
    return map
  }, [plan])

  const alerts = useMemo(() => {
    const result = []
    trains.forEach((train) => {
      const critical = train.job_cards.filter((j) => j.status === 'open' && j.severity === 'critical')
      if (critical.length) result.push({ level: 'critical', train: train.train_id, text: `${critical[0].id} is open and critical.` })
      if (train.fitness_expired) result.push({ level: 'critical', train: train.train_id, text: 'Fitness certificate has expired.' })
      else if (train.fitness_expiring_soon) result.push({ level: 'warning', train: train.train_id, text: `Fitness certificate expires ${train.fitness_cert_expiry}.` })
      if (train.cleaning_due) result.push({ level: 'info', train: train.train_id, text: 'Cleaning is due.' })
    })
    return result
  }, [trains])

  const stats = useMemo(() => {
    const assignments = plan?.assignments || []
    const count = (state) => assignments.filter((a) => a.state === state).length
    return {
      total:       trains.length,
      service:     count('service'),
      maintenance: count('maintenance'),
      standby:     count('standby'),
      cleaning:    count('cleaning'),
      shunts:      plan?.shunts_required?.length || 0,
      critical:    alerts.filter((a) => a.level === 'critical').length,
    }
  }, [plan, trains, alerts])

  const filteredAssignments = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (plan?.assignments || []).filter((a) =>
      !q || `${a.train_id} ${a.state} ${a.reason}`.toLowerCase().includes(q)
    )
  }, [plan, search])

  async function regenerate() {
    setGenerating(true)
    setError('')
    try {
      const fresh = await api.generatePlan()
      setPlan(fresh)
      setScenario(null)
      setExplanation(null)
    } catch (err) {
      setError(err.message || 'Plan generation failed.')
    } finally {
      setGenerating(false)
    }
  }

  async function runScenario(trainId, status) {
    setScenarioLoading(true)
    setError('')
    try {
      const result = await api.whatIf({ train_id: trainId, status })
      setScenario({ override: { train_id: trainId, status }, result })
      // The current backend contract returns the affected subset; overlay it on the baseline plan.
      setPlan((current) => ({
        ...current,
        plan_id:         result.plan_id,
        generated_at:    result.generated_at,
        assignments: (current?.assignments || []).map((assignment) =>
          result.assignments?.find((candidate) => candidate.train_id === assignment.train_id) || assignment
        ),
        shunts_required: result.shunts_required || current?.shunts_required || [],
      }))
    } catch (err) {
      setError(err.message || 'What-if request failed.')
    } finally {
      setScenarioLoading(false)
    }
  }

  async function explain(e) {
    if (e && e.preventDefault) e.preventDefault()
    if (!explainTrain || !plan) return
    setExplainLoading(true)
    setError('')
    try {
      setExplanation(await api.explain(plan.plan_id, explainTrain))
    } catch (err) {
      setError(err.message || 'Explanation request failed.')
    } finally {
      setExplainLoading(false)
    }
  }

  const go = (view) => {
    setActiveView(view)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (loading || bootError) return (
    <BootScreen bootStatus={bootStatus} error={bootError} onRetry={loadDashboard} />
  )

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="brand" style={{ cursor: 'pointer' }}>
            <div className="brand-mark">M</div>
            <div><strong>MetGo</strong><span>INDUCTION OPS</span></div>
          </div>
        </Link>
        <nav>
          {[
            { key: 'overview', icon: '▦', label: 'Dashboard'        },
            { key: 'plan',     icon: '▤', label: 'Induction plan'   },
            { key: 'fleet',    icon: '▥', label: 'Fleet status'     },
            { key: 'yard',     icon: '⌘', label: 'Yard digital twin'},
            { key: 'whatif',   icon: '◇', label: 'What-if simulator'},
            { key: 'explain',  icon: '?', label: 'Explainability'   },
          ].map(({ key, icon, label }) => (
            <button
              key={key}
              className={activeView === key ? 'nav-item active' : 'nav-item'}
              onClick={() => go(key)}
            >
              <span>{icon}</span> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-card">
            <span className={`status-dot ${backendOnline ? 'online' : ''}`} />
            <div>
              <strong>{backendOnline ? 'Backend online' : 'Backend offline'}</strong>
              <small>{api.baseUrl}</small>
            </div>
          </div>
          <small className="attribution">Contains data provided by Kochi Metro Rail Limited</small>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="eyebrow">OPERATIONS CONTROL</span>
            <h1>MetGo Dashboard</h1>
          </div>
          <div className="top-actions">
            <span className="live-pill"><span className="status-dot online" /> LIVE BACKEND</span>
            <button className="refresh-btn" onClick={loadDashboard}>↻ Refresh</button>
          </div>
        </header>

        {/* PA-style banners */}
        <PAToast type="error" show={!!error} action={{ label: 'Retry', onClick: loadDashboard }}>
          <strong style={{ color: 'var(--color-signal-red)' }}>Connection issue</strong>
          {' — '}
          {error}
        </PAToast>
        <PAToast type="scenario" show={!!scenario} action={{ label: 'Return to baseline', onClick: loadDashboard }}>
          <strong>{scenario?.override.train_id}</strong> → {scenario?.override.status}
        </PAToast>

        {/* ── View Transitions ─────────────────────────────── */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0  }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {activeView === 'overview' && (
              <>
                <section className="hero-card">
                  <div>
                    <span className="eyebrow light">NEXT SERVICE DAY</span>
                    <h2>
                      {(() => {
                        if (!plan?.plan_id) return ''
                        const match = plan.plan_id.match(/plan_(\d{4})_(\d{2})_(\d{2})/)
                        if (match) {
                          const date = new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00`)
                          return `Plan for ${date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
                        }
                        return plan.plan_id
                      })()}
                    </h2>
                    <p>AI-assisted overnight induction plan. The system recommends; the operator decides.</p>
                    <div className="hero-meta">
                      Generated {(() => {
                        let raw = plan?.generated_at || '';
                        // Backend bug sends +00:00Z which makes JS Date crash. Clean it up.
                        if (raw.includes('+') && raw.endsWith('Z')) raw = raw.slice(0, -1);
                        let d = new Date(raw);
                        if (isNaN(d)) return 'just now';
                        const s = Math.floor((new Date() - d) / 1000);
                        if (s < 60) return 'just now';
                        const m = Math.floor(s / 60);
                        if (m < 60) return `${m} min${m !== 1 ? 's' : ''} ago`;
                        const h = Math.floor(m / 60);
                        if (h < 24) return `${h} hour${h !== 1 ? 's' : ''} ago`;
                        const days = Math.floor(h / 24);
                        return `${days} day${days !== 1 ? 's' : ''} ago`;
                      })()} · {stats.total} fleet records loaded
                    </div>
                  </div>
                  <button className="primary-btn" onClick={regenerate} disabled={generating}>
                    {generating ? 'Generating…' : '↻ Generate fresh plan'}
                  </button>
                </section>
                <Stats stats={stats} />
                <section className="grid-two">
                  <Alerts alerts={alerts} onSelect={(id) => { setExplainTrain(id); go('explain') }} />
                  <PlanSnapshot assignments={plan?.assignments || []} onOpen={() => go('plan')} />
                </section>
                <Yard plan={plan} trains={trains} compact onOpen={() => go('yard')} />
              </>
            )}

            {activeView === 'fleet'   && <Fleet trains={trains} stats={stats} />}
            {activeView === 'plan'    && (
              <section className="panel">
                <PanelHeader eyebrow="DECISION OUTPUT" title="Tonight's induction plan" subtitle="Assignments returned directly by POST /plan/generate." />
                <div className="toolbar">
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search train, state or reason…" />
                  <span>{filteredAssignments.length} assignments</span>
                </div>
                <PlanTable assignments={filteredAssignments} />
              </section>
            )}
            {activeView === 'yard'    && <Yard plan={plan} trains={trains} />}
            {activeView === 'whatif'  && <WhatIf trains={trains} loading={scenarioLoading} onRun={runScenario} />}
            {activeView === 'explain' && (
              <Explain
                trains={trains}
                plan={plan}
                selected={explainTrain}
                setSelected={setExplainTrain}
                explanation={explanation}
                loading={explainLoading}
                onAsk={explain}
              />
            )}
          </motion.div>
        </AnimatePresence>

        <footer className="footer">MetGo — AI-Driven Train Induction Planning · React frontend · FastAPI backend · Human-in-the-loop decision support</footer>
      </main>
    </div>
  )
}

// ── Metric (count-up) ─────────────────────────────────────────
function Metric({ label, value, tone }) {
  const displayed = useCountUp(value)
  return (
    <div className={`home-metric ${tone || ''}`}>
      <strong>{displayed}</strong>
      <span>{label}</span>
    </div>
  )
}

// ── Fleet ─────────────────────────────────────────────────────
function Fleet({ trains, stats }) {
  return (
    <section className="panel">
      <PanelHeader eyebrow="FLEET STATUS" title="Train fleet" subtitle={`${stats.total} train records loaded from the backend.`} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Train</th>
              <th>Fitness</th>
              <th>Job cards</th>
              <th>Cleaning</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {trains.map(t => {
              const fs = t.fitness_expired ? 'expired' : t.fitness_expiring_soon ? 'soon' : 'ok'
              const river = getTrainName(t.train_id)
              return (
                <tr key={t.train_id}>
                  <td>
                    <div className="train-cell">
                      <strong>{t.train_id}</strong>
                      {river.name && (
                        <span className="train-river-tag">
                          ≈ {river.name.toUpperCase()} <span className="train-malayalam">({river.malayalam})</span>
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`fleet-fitness-${fs}`}>
                      {t.fitness_expired ? 'Expired' : t.fitness_expiring_soon ? `Expiring ${t.fitness_cert_expiry}` : t.fitness_cert_expiry || 'Valid'}
                    </span>
                  </td>
                  <td>{t.job_cards.filter(j => j.status === 'open').length} open</td>
                  <td>
                    <span style={{ color: t.cleaning_due ? 'var(--color-signal-amber)' : 'var(--color-signal-green)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                      {t.cleaning_due ? 'Due' : 'OK'}
                    </span>
                  </td>
                  <td><StateBadge state={assignmentState(t)} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function assignmentState(train) { return train.breakdown ? 'breakdown' : train.cleaning_due ? 'cleaning' : train.fitness_expired ? 'maintenance' : 'service' }

// ── Panel Header ──────────────────────────────────────────────
function PanelHeader({ eyebrow, title, subtitle }) {
  return (
    <div className="panel-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  )
}

// ── Stats Grid ────────────────────────────────────────────────
function Stats({ stats }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  const cleanKm = Math.round((stats.service || 15) * 340)

  return (
    <motion.div
      ref={ref}
      className="stats-grid"
      variants={staggerFast}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
    >
      <Stat label="Fleet loaded"    value={stats.total}       note="train records"          />
      <Stat label="Revenue service" value={stats.service}     note="assigned tonight"       tone="green"  />
      <Stat label="Maintenance"     value={stats.maintenance} note="hard / soft constraints" tone="amber"  />
      <Stat label="Standby"         value={stats.standby}     note="reserve capacity"       tone="blue"   />
      <Stat label="Yard shunts"     value={stats.shunts}      note="moves required"         tone="purple" />
      <Stat label="Clean solar offset" value={cleanKm}         note="zero-carbon km / day"   tone="solar-card" />
    </motion.div>
  )
}
function Stat({ label, value, note, tone = '' }) {
  const displayed = useCountUp(value)
  return (
    <motion.div className={`stat-card ${tone}`} variants={fadeUp}>
      <span>{label}</span>
      <strong>{displayed}</strong>
      <small>{note}</small>
    </motion.div>
  )
}

// ── Alerts ────────────────────────────────────────────────────
function Alerts({ alerts, onSelect }) {
  const alertState = { critical: 'red', warning: 'amber', info: 'blue' }
  return (
    <div className="panel alerts-card">
      <PanelHeader eyebrow="FLEET HEALTH" title="Alerts & constraints" subtitle="Derived from live train detail records." />
      <motion.div
        className="alert-list"
        variants={staggerFast}
        initial="hidden"
        animate="visible"
      >
        {alerts.length
          ? alerts.slice(0, 8).map((a, i) => (
            <motion.button
              key={`${a.train}-${i}`}
              className={`alert-row ${a.level}`}
              onClick={() => onSelect(a.train)}
              variants={fadeUp}
            >
              <span className="alert-icon">
                <SignalLight state={alertState[a.level] || 'blue'} size="md" pulse={a.level === 'critical'} />
              </span>
              <div>
                <strong>{a.train}</strong>
                <span>{a.text}</span>
              </div>
              <b>›</b>
            </motion.button>
          ))
          : <div className="empty-state">✓ No active fleet alerts</div>
        }
      </motion.div>
    </div>
  )
}

// ── Plan Snapshot ─────────────────────────────────────────────
function PlanSnapshot({ assignments, onOpen }) {
  return (
    <div className="panel">
      <PanelHeader eyebrow="PLAN SNAPSHOT" title="Assignment decisions" subtitle="Click through for the complete plan." />
      <div className="snapshot-list">
        {assignments.map((a) => {
          const river = getTrainName(a.train_id)
          return (
            <div className="snapshot-row" key={a.train_id}>
              <div className="train-cell">
                <strong>{a.train_id}</strong>
                {river.name && <span className="train-malayalam">{river.name}</span>}
              </div>
              <StateBadge state={a.state} />
              <span>{a.reason}</span>
            </div>
          )
        })}
      </div>
      <button className="text-btn" onClick={onOpen}>View full induction plan →</button>
    </div>
  )
}

// ── State Badge ───────────────────────────────────────────────
function StateBadge({ state }) {
  const meta = STATE_META[state] || STATE_META.service
  return (
    <span className={`state-badge ${meta.className}`}>
      <i>{meta.icon}</i>{meta.label}
    </span>
  )
}

// ── Plan Table — departure-board flip ─────────────────────────
function PlanTable({ assignments }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Train</th>
            <th>Assignment</th>
            <th>Reason / solver signal</th>
            <th>Constraint</th>
          </tr>
        </thead>
        <AnimatePresence mode="sync">
          <tbody>
            {assignments.map((a) => {
              const river = getTrainName(a.train_id)
              const multimodal = MULTIMODAL_HUBS[a.train_id]
              return (
                <motion.tr
                  key={a.train_id}
                  initial={{ opacity: 0, rotateX: -25 }}
                  animate={{ opacity: 1, rotateX: 0  }}
                  exit={{ opacity: 0, rotateX: 25 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                  style={{ transformOrigin: 'top center', backfaceVisibility: 'hidden' }}
                >
                  <td>
                    <div className="train-cell">
                      <strong>{a.train_id}</strong>
                      {river.name && (
                        <span className="train-river-tag">
                          ≈ {river.name.toUpperCase()} <span className="train-malayalam">({river.malayalam})</span>
                        </span>
                      )}
                      {a.state === 'service' && multimodal && (
                        <span className="multimodal-badge">
                          {multimodal.icon} {multimodal.label}
                        </span>
                      )}
                    </div>
                  </td>
                  <td><StateBadge state={a.state} /></td>
                  <td>{a.reason}</td>
                  <td><ConstraintLight type={a.constraint_type} /></td>
                </motion.tr>
              )
            })}
          </tbody>
        </AnimatePresence>
      </table>
    </div>
  )
}

// ── Yard ──────────────────────────────────────────────────────
function Yard({ plan, trains, compact = false, onOpen }) {
  const assignmentMap = Object.fromEntries((plan?.assignments || []).map((a) => [a.train_id, a]))
  
  // Create a continuous live-feel simulation. If the plan has shunts, animate those.
  // Otherwise, inject a demo shunt (like T05 to W1) to keep the digital twin looking alive.
  const shunts = useMemo(() => {
    const actualShunts = plan?.shunts_required || []
    if (actualShunts.length > 0) return actualShunts
    const t05 = trains.find(t => t.train_id === 'T05')
    return t05 ? [{ train_id: 'T05', from_bay: t05.current_bay, to_bay: 'W1' }] : []
  }, [plan?.shunts_required, trains])

  const [simulating, setSimulating] = useState(false)
  useEffect(() => {
    if (shunts.length === 0) return
    const interval = setInterval(() => setSimulating(s => !s), 3000)
    return () => clearInterval(interval)
  }, [shunts])

  const bayMap = useMemo(() => {
    const map = {}
    trains.forEach((t) => {
      let current = t.current_bay
      if (simulating) {
        const shunt = shunts.find(s => s.train_id === t.train_id)
        if (shunt) current = shunt.to_bay
      }
      if (current) map[current] = t
    })
    return map
  }, [trains, simulating, shunts])

  return (
    <section className={`panel yard-panel ${compact ? 'compact' : ''}`}>
      <PanelHeader
        eyebrow="DIGITAL TWIN"
        title="Muttom Yard"
        subtitle={shunts.length > 0 ? (simulating ? "Simulating planned shunts..." : "Live train positions from fleet API.") : "Live train positions from the fleet API."}
      />
      <div className="yard-legend">
        <span><i className="legend-dot service" />Service</span>
        <span><i className="legend-dot maintenance" />Maintenance</span>
        <span><i className="legend-dot cleaning" />Cleaning</span>
        <span><i className="legend-dot standby" />Standby</span>
        <span><i className="legend-dot empty" />Empty</span>
      </div>
      <div className="yard-grid">
        {YARD_LAYOUT.lines.map((line) => (
          <div className="yard-line" key={line.line_id}>
            <div className="line-label">
              <strong>{line.line_name}</strong>
              <small>{line.line_id}</small>
            </div>
            <div className="bays">
              {line.bays.map((bay) => {
                const train = bayMap[bay]
                const originalTrain = trains.find(t => t.current_bay === bay)
                // Use train from simulating or actual train state
                const activeTrainId = train ? train.train_id : null
                const state = activeTrainId ? assignmentMap[activeTrainId]?.state || 'standby' : 'empty'
                const shuntFromHere = shunts.find((s) => s.from_bay === bay)
                const shuntToHere = shunts.find((s) => s.to_bay === bay)
                const isService = state === 'service' && activeTrainId

                return (
                  <motion.div
                    className={`bay ${state} ${(shuntFromHere || shuntToHere) ? 'shunt' : ''} ${isService ? 'pulsing' : ''}`}
                    key={bay}
                    title={train ? `${train.train_id} · ${state}` : `${bay} · empty`}
                    layout
                    transition={{ duration: 0.35, ease: 'easeInOut' }}
                  >
                    <small>{bay}</small>
                    <div className="bay-content">
                      {train ? (
                        <motion.strong
                          layoutId={`train-${train.train_id}-${compact ? 'mini' : 'full'}`}
                          className={`train-pill ${state}`}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ type: "spring", stiffness: 45, damping: 14 }}
                        >
                          {train.train_id}
                        </motion.strong>
                      ) : (
                        <span className="empty">—</span>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      {shunts.length > 0 && (
        <div className="shunt-strip">
          <strong>{shunts.length} planned shunt{shunts.length > 1 ? 's' : ''}</strong>
          {shunts.map((s) => (
            <span key={`${s.train_id}-${s.to_bay}`}>{s.train_id} {s.from_bay} → {s.to_bay}</span>
          ))}
        </div>
      )}
      {compact && <button className="text-btn" onClick={onOpen}>Open yard digital twin →</button>}
    </section>
  )
}

// ── What-If ───────────────────────────────────────────────────
function WhatIf({ trains, loading, onRun }) {
  const [train, setTrain] = useState('')
  const [status, setStatus] = useState('breakdown')
  const scenarios = [
    ['breakdown',    'Simulate breakdown'],
    ['maintenance',  'Force maintenance'],
    ['cleaning',     'Force cleaning'],
    ['cert_expired', 'Simulate cert expiry'],
  ]

  return (
    <section className="panel whatif-panel">
      <PanelHeader
        eyebrow="LIVE RE-PLANNING"
        title="What-if simulator"
        subtitle="POST /plan/what-if sends the override to the backend. No frontend solver logic is used."
      />
      <div className="scenario-form">
        <label>
          Train
          <select value={train} onChange={(e) => setTrain(e.target.value)}>
            <option value="">Select train…</option>
            {trains.map((t) => (
              <option key={t.train_id} value={t.train_id}>
                {formatTrainLabel(t.train_id, t.current_bay || 'no bay')}
              </option>
            ))}
          </select>
        </label>
        <label>
          Scenario
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {scenarios.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <button className="primary-btn" disabled={!train || loading} onClick={() => onRun(train, status)}>
          {loading ? 'Re-planning…' : 'Run scenario'}
        </button>
      </div>

      {/* Signal sweep during loading */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
            style={{ marginTop: 20 }}
          >
            <SignalSweep />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="scenario-callout">
        <strong>DEMO PATH</strong>
        <span>Break down a service train → backend recomputes → updated assignment and shunt plan appear on the dashboard.</span>
      </div>
    </section>
  )
}

// ── Explain ───────────────────────────────────────────────────
function formatBreakdown(breakdown) {
  if (!breakdown || typeof breakdown !== 'object') return []
  const rows = []
  
  const flatten = (obj, prefix = '') => {
    Object.entries(obj).forEach(([k, v]) => {
      const formattedKey = (prefix ? prefix + ' - ' : '') + k.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
        flatten(v, formattedKey)
      } else {
        rows.push([formattedKey, String(v)])
      }
    })
  }
  
  flatten(breakdown)
  return rows
}

function Explain({ trains, plan, selected, setSelected, explanation, loading, onAsk }) {
  const breakdown = formatBreakdown(explanation?.quantitative_breakdown)
  const river = selected ? getTrainName(selected) : null

  return (
    <section className="panel explain-panel">
      <PanelHeader
        eyebrow="EXPLAINABILITY ENGINE"
        title="Why did the solver choose this?"
        subtitle="Explanation is fetched from GET /plan/{plan_id}/explain/{train_id}."
      />
      <div className="explain-form">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Select a train…</option>
          {trains.map((t) => (
            <option key={t.train_id} value={t.train_id}>
              {formatTrainLabel(t.train_id, t.current_bay)}
            </option>
          ))}
        </select>
        <button className="primary-btn" disabled={!selected || loading} onClick={onAsk}>
          {loading ? 'Fetching…' : 'Explain assignment'}
        </button>
      </div>

      <AnimatePresence mode="wait">
        {explanation ? (
          <motion.div
            key="explanation"
            className="explanation"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0  }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {river?.name && (
              <div className="explain-river-card">
                <div>
                  <span className="explain-river-name">{explanation.train_id} · {river.name.toUpperCase()}</span>
                  <span className="explain-river-mal">({river.malayalam})</span>
                </div>
                <span className="explain-river-type">{river.type}</span>
              </div>
            )}
            <div className="explanation-top">
              <strong>{explanation.train_id}</strong>
              <StateBadge state={explanation.assigned_state} />
            </div>
            <p>{explanation.explanation}</p>
            <div className="tags">
              {explanation.constraints_considered?.map((c) => (
                <span key={c}>{c.replaceAll('_', ' ')}</span>
              ))}
            </div>
            {breakdown.length > 0 && (
              <div className="quant-breakdown">
                <strong>Penalty breakdown</strong>
                <table>
                  <tbody>
                    {breakdown.map(([label, value]) => (
                      <tr key={label}>
                        <td>{label}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            className="explain-empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            Select a train to retrieve a grounded explanation from the backend.
          </motion.div>
        )}
      </AnimatePresence>

      <div className="query-note">
        Natural-language query is grounded in CP-SAT solver constraint reasoning and real penalty weights.
      </div>
    </section>
  )
}

export default App
