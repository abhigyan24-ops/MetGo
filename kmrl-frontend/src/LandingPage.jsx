import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform, useInView, useMotionValue, useSpring, useReducedMotion, AnimatePresence } from 'framer-motion';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import { MeshGradient } from '@paper-design/shaders-react';
import NetworkMap from './components/NetworkMap';
import './LandingPage.css';

gsap.registerPlugin(ScrollTrigger, MotionPathPlugin);

// ── Yard Layout (Mock for Landing Page) ──────────────────────
const MOCK_YARD_LAYOUT = {
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
const MOCK_TRAINS = [
  { train_id: 'T01', status: 'service', current_bay: 'B01', fitness_days: 120, mileage: 45000 },
  { train_id: 'T02', status: 'service', current_bay: 'B02', fitness_days: 85, mileage: 60000 },
  { train_id: 'T03', status: 'standby', current_bay: 'B07', fitness_days: 20, mileage: 80000 },
  { train_id: 'T04', status: 'cleaning', current_bay: 'W01', fitness_days: 100, mileage: 30000 },
  { train_id: 'T05', status: 'maintenance', current_bay: 'M01', fitness_days: 0, mileage: 90000 },
  { train_id: 'T06', status: 'service', current_bay: 'B13', fitness_days: 200, mileage: 15000 },
  { train_id: 'T07', status: 'standby', current_bay: 'B14', fitness_days: 150, mileage: 25000 },
];

function MockYard() {
  const getTrainForBay = (bayId) => MOCK_TRAINS.find(t => t.current_bay === bayId)
  return (
    <div className="lp-yard-preview">
      <div className="lp-yard-header">
        <div className="lp-dots"><span/><span/><span/></div>
        <div className="lp-yard-title">Muttom Yard Digital Twin</div>
        <div className="lp-live-badge"><span className="status-dot online"></span> LIVE</div>
      </div>
      <div className="lp-yard-body">
         <div className="yard-grid" style={{ pointerEvents: 'none' }}>
           {MOCK_YARD_LAYOUT.lines.map(line => (
             <div key={line.line_id} className="yard-line">
               <div className="line-label">
                 <strong>{line.line_name}</strong>
                 <small>{line.line_id}</small>
               </div>
               <div className="bays">
                 {line.bays.map(bayId => {
                   const train = getTrainForBay(bayId)
                   return (
                     <div key={bayId} className={`bay ${train ? train.status : ''} ${train?.status === 'service' ? 'pulsing' : ''}`}>
                       <small>{bayId}</small>
                       {train ? (
                         <>
                           <strong>{train.train_id}</strong>
                           <em>{train.status}</em>
                         </>
                       ) : (
                         <span>—</span>
                       )}
                     </div>
                   )
                 })}
               </div>
             </div>
           ))}
         </div>
      </div>
    </div>
  )
}

// ── Metric Count-up ───────────────────────────────────────────
function useCountUp(endValue, duration = 1500) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    let startTimestamp = null
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp
      const progress = Math.min((timestamp - startTimestamp) / duration, 1)
      const easeOut = 1 - Math.pow(1 - progress, 3)
      setValue(Math.floor(easeOut * endValue))
      if (progress < 1) window.requestAnimationFrame(step)
    }
    window.requestAnimationFrame(step)
  }, [endValue, duration])
  return value
}

function Metric({ label, value, tone, prefix = '', suffix = '' }) {
  const displayed = useCountUp(value)
  return (
    <div className={`lp-metric lp-metric-${tone || 'default'}`}>
      <strong>{prefix}{displayed.toLocaleString()}{suffix}</strong>
      <span>{label}</span>
    </div>
  )
}

// ── Polish Pass Components ─────────────────────────────────────
function MagneticButton({ children }) {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 300, damping: 20 });
  const springY = useSpring(y, { stiffness: 300, damping: 20 });
  const prefersReducedMotion = useReducedMotion();

  const handleMouseMove = (e) => {
    if (prefersReducedMotion) return;
    const rect = ref.current.getBoundingClientRect();
    const relX = e.clientX - (rect.left + rect.width / 2);
    const relY = e.clientY - (rect.top + rect.height / 2);
    x.set(relX * 0.35); // subtle magnet strength
    y.set(relY * 0.35);
  };
  const handleMouseLeave = () => { 
    if (prefersReducedMotion) return;
    x.set(0); y.set(0); 
  };

  return (
    <motion.div
      ref={ref}
      style={{ display: 'inline-block', x: springX, y: springY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {children}
    </motion.div>
  );
}

function SpotlightCard({ children, className = '' }) {
  const prefersReducedMotion = useReducedMotion();
  const handleMouseMove = (e) => {
    if (prefersReducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--x', `${e.clientX - rect.left}px`);
    e.currentTarget.style.setProperty('--y', `${e.clientY - rect.top}px`);
  };
  return (
    <div className={`spotlight-card ${className}`} onMouseMove={handleMouseMove}>
      {children}
    </div>
  );
}

function MiniDemo() {
  const [trains, setTrains] = useState([
    { id: 'T01', status: 'service', label: 'Service (L1)' },
    { id: 'T02', status: 'service', label: 'Service (L2)' },
    { id: 'T03', status: 'service', label: 'Service (L3)' },
    { id: 'T07', status: 'standby', label: 'Standby' },
    { id: 'T12', status: 'maintenance', label: 'Maintenance' },
  ]);
  const [log, setLog] = useState("System nominal. All service trains active.");
  const [clickedTrain, setClickedTrain] = useState(null);

  const toggleBreakdown = (trainId) => {
    setTrains(prev => {
      const newTrains = [...prev];
      const targetIdx = newTrains.findIndex(t => t.id === trainId);
      const target = newTrains[targetIdx];

      if (target.status === 'service') {
        const standbyIdx = newTrains.findIndex(t => t.status === 'standby');
        if (standbyIdx !== -1) {
          const standby = newTrains[standbyIdx];
          newTrains[targetIdx] = { ...target, status: 'breakdown', label: 'Breakdown' };
          newTrains[standbyIdx] = { ...standby, status: 'service', label: target.label };
          setLog(`${target.id} breakdown detected. ${standby.id} promoted from standby — valid fitness certificate, no open job cards.`);
        } else {
          newTrains[targetIdx] = { ...target, status: 'breakdown', label: 'Breakdown' };
          setLog(`${target.id} breakdown detected. No standby trains available!`);
        }
      }
      return newTrains;
    });
    setClickedTrain(trainId);
    setTimeout(() => setClickedTrain(null), 300);
  };

  const serviceCount = trains.filter(t => t.status === 'service').length;

  return (
    <div className="lp-mini-demo">
      <div className="mini-demo-bg-pattern"></div>
      
      <div className="mini-demo-header">
         <div className="mdh-left">
           <span className="live-pulse-dot"></span>
           <strong>LIVE PREVIEW</strong>
         </div>
         <span className="status-counter">Trains in Service: {serviceCount} / 3</span>
      </div>

      <div className="lp-mini-demo-grid">
        {trains.map(t => (
          <motion.div 
            layout 
            key={t.id} 
            className={`lp-mini-train ${t.status} ${clickedTrain === t.id ? 'flash' : ''}`}
            onClick={() => toggleBreakdown(t.id)}
            whileHover={{ scale: t.status === 'service' ? 1.02 : 1 }}
            animate={t.status === 'service' ? { x: [0, 2, 0] } : {}}
            transition={t.status === 'service' ? { repeat: Infinity, duration: 2, ease: "easeInOut", delay: Math.random() } : {}}
            style={{ cursor: t.status === 'service' ? 'pointer' : 'default' }}
          >
            <div className="mini-train-info">
              <strong>{t.id}</strong>
              <span>{t.label}</span>
            </div>
            <div className="mini-train-status">
              <span className="mini-badge">{t.status.toUpperCase()}</span>
            </div>
            {t.status === 'service' && <div className="mini-click-hint">CLICK TO FAIL</div>}
          </motion.div>
        ))}
      </div>
      <div className="lp-mini-demo-log">
        <span className="log-indicator"></span>
        <p>{log}</p>
      </div>
      <small className="lp-mini-demo-disclaimer">
        Interactive preview — try it, then open the full dashboard for the real optimizer.
      </small>
    </div>
  );
}

// --- VIGNETTES ---
const VignettePatternA = ({ topLabel, bottomLabel, pillIcon, pillText, colorVar }) => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const particles = Array.from({ length: 7 });
  const isCycling = Array.isArray(pillText);
  const [cycleIndex, setCycleIndex] = useState(0);

  useEffect(() => {
    if (isCycling && !prefersReducedMotion) {
      const timer = setInterval(() => {
        setCycleIndex(prev => (prev + 1) % pillText.length);
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [isCycling, prefersReducedMotion, pillText]);

  const currentPillText = isCycling ? pillText[cycleIndex] : pillText;

  return (
    <div className="vignette-container">
      <div className="vignette-panel">
        <div className="vp-icon" style={{ background: colorVar }}></div>
        <div className="vp-text">{topLabel}</div>
        <div className="vp-detail"></div>
      </div>
      
      <div className="vignette-connector">
        <div className="vc-line"></div>
        {!prefersReducedMotion && particles.map((_, i) => (
           <motion.div 
             key={i}
             className="vc-particle"
             style={{ backgroundColor: colorVar }}
             animate={{ y: [0, 80], opacity: [0, 1, 0] }}
             transition={{ duration: 2, repeat: Infinity, delay: i * 0.3, ease: "linear" }}
           />
        ))}
        <div className="vc-pill" style={{ '--pill-color': colorVar }}>
          <span className="vc-pill-icon">{pillIcon}</span>
          <span className="vc-pill-text">
            <AnimatePresence mode="wait">
              <motion.span
                key={currentPillText}
                initial={isCycling && !prefersReducedMotion ? { opacity: 0, y: 5 } : false}
                animate={{ opacity: 1, y: 0 }}
                exit={isCycling && !prefersReducedMotion ? { opacity: 0, y: -5 } : undefined}
                transition={{ duration: 0.2 }}
              >
                {currentPillText}
              </motion.span>
            </AnimatePresence>
          </span>
        </div>
      </div>

      <div className="vignette-panel">
        <div className="vp-icon" style={{ background: colorVar }}></div>
        <div className="vp-text">{bottomLabel}</div>
        <div className="vp-detail"></div>
      </div>
    </div>
  );
};

const VignettePatternB = ({ cards, colorVar }) => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!prefersReducedMotion) {
      const timer = setInterval(() => {
        setActiveIndex(prev => (prev + 1) % cards.length);
      }, 4000);
      return () => clearInterval(timer);
    }
  }, [cards.length, prefersReducedMotion]);

  return (
    <div className="vignette-container">
      <div className="vignette-b-stack">
        {cards.map((card, idx) => {
           const offset = (idx - activeIndex + cards.length) % cards.length;
           
           return (
             <motion.div 
               key={idx}
               className="vignette-b-card"
               animate={prefersReducedMotion ? false : {
                 y: offset * -20,
                 x: offset * 20,
                 scale: 1 - offset * 0.05,
                 opacity: 1 - offset * 0.3,
                 zIndex: cards.length - offset
               }}
               initial={false}
               transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
             >
                <div className="vb-card-header">
                  <div className="vb-card-icon" style={{ background: colorVar }}></div>
                  <strong>{card.id}</strong>
                </div>
                <div className="vb-card-status">
                   <span>✓</span>
                   <span>{card.status}</span>
                </div>
             </motion.div>
           )
        })}
      </div>
    </div>
  );
};

const VignettePatternC = ({ colorVar }) => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  return (
    <div className="vignette-container">
       <svg width="200" height="200" viewBox="0 0 200 200" className="vignette-c-svg">
         <g stroke="rgba(255,255,255,0.1)" strokeWidth="2">
            <line x1="100" y1="40" x2="40" y2="120" />
            <line x1="100" y1="40" x2="160" y2="120" />
            <line x1="40" y1="120" x2="100" y2="180" />
            <line x1="160" y1="120" x2="100" y2="180" />
            <line x1="40" y1="120" x2="160" y2="120" />
         </g>
         
         <g fill="#06080a" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5">
            <circle cx="100" cy="40" r="10" />
            <circle cx="40" cy="120" r="10" />
            <circle cx="160" cy="120" r="10" />
            <circle cx="100" cy="180" r="10" />
         </g>

         <g fill={colorVar}>
            <circle cx="100" cy="40" r="4" opacity="0.5" />
            <circle cx="40" cy="120" r="4" opacity="0.5" />
            <circle cx="160" cy="120" r="4" opacity="0.5" />
            <circle cx="100" cy="180" r="4" opacity="0.5" />
         </g>

         {!prefersReducedMotion && (
           <motion.circle 
             r="4" 
             fill={colorVar}
             style={{ filter: `drop-shadow(0 0 8px ${colorVar})` }}
             animate={{
                cx: [100, 40, 100, 100],
                cy: [40, 120, 180, 40]
             }}
             transition={{
                duration: 4,
                ease: "linear",
                repeat: Infinity
             }}
           />
         )}
       </svg>
    </div>
  );
};

// ── Main Landing Page ────────────────────────────────────────
export default function LandingPage() {
  const { scrollYProgress } = useScroll();
  const heroY = useTransform(scrollYProgress, [0, 0.2], [0, -50]);
  
  const isMobileOrReduced = typeof window !== 'undefined' && 
    (window.matchMedia('(max-width: 768px)').matches || 
     window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  // Hero SVG GSAP Animation
  const trainRef = useRef(null);
  useEffect(() => {
    if (isMobileOrReduced) return;
    const ctx = gsap.context(() => {
      gsap.to(trainRef.current, {
        motionPath: {
          path: '#hero-rail',
          align: '#hero-rail',
          alignOrigin: [0.5, 0.5],
          autoRotate: true
        },
        duration: 15,
        repeat: -1,
        ease: 'none'
      });
    });
    return () => ctx.revert();
  }, [isMobileOrReduced]);

  // Sync Lenis and ScrollTrigger
  useEffect(() => {
    const syncScrollTrigger = (time) => {
      ScrollTrigger.update();
    };
    gsap.ticker.add(syncScrollTrigger);
    return () => gsap.ticker.remove(syncScrollTrigger);
  }, []);

  // Continuous Pipeline Rail Animation
  const pipelineRef = useRef(null);
  useEffect(() => {
    const ctx = gsap.context(() => {
      const wrapper = pipelineRef.current;
      const train = wrapper.querySelector('.global-rail-train');
      const trackFill = wrapper.querySelector('.global-rail-fill');
      const nodes = gsap.utils.toArray('.global-rail-node');
      const sections = gsap.utils.toArray('.pipeline-section');
      const railCol = wrapper.querySelector('.global-rail-col');
      if (!wrapper || !train || !trackFill || !railCol) return;

      const colors = ['#2f7dfa', '#f5a623', '#8b6ef5', '#f5487c', '#3dd68c'];

      // Set initial states
      gsap.set(sections, { opacity: 0, y: 50 });
      gsap.set(sections[0], { opacity: 1, y: 0 });
      nodes[0].classList.add('active');

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: wrapper,
          start: 'top top',
          end: '+=4000', // 4000px of scrolling for 5 sections
          pin: true,
          scrub: isMobileOrReduced ? true : 0.5,
          onUpdate: (self) => {
            const time = self.progress * 90;
            nodes.forEach((node, i) => {
               const activationTime = i === 0 ? 0 : (i - 1) * 20 + 20;
               if (time >= activationTime - 5) {
                 node.classList.add('active');
               } else {
                 node.classList.remove('active');
               }
            });
          }
        }
      });

      const railPositions = ['0%', '25%', '50%', '75%', '100%'];
      
      // Phase 0: Read Section 0 (time 0-10)
      tl.to({}, { duration: 10 });

      for (let i = 0; i < 4; i++) {
        const transStart = i * 20 + 10;
        const readStart = transStart + 10;
        
        // Transition Phase (duration 10)
        tl.to(train, { top: railPositions[i+1], duration: 10, ease: 'power1.inOut' }, transStart);
        tl.to(trackFill, { height: railPositions[i+1], duration: 10, ease: 'power1.inOut' }, transStart);
        tl.to(railCol, { '--rail-color': colors[i+1], duration: 10, ease: 'none' }, transStart);
        
        tl.to(sections[i], { opacity: 0, y: -50, duration: 10 }, transStart);
        tl.to(sections[i+1], { opacity: 1, y: 0, duration: 10 }, transStart);

        // Read Phase (duration 10)
        tl.to({}, { duration: 10 }, readStart);
      }

    }, pipelineRef);
    return () => ctx.revert();
  }, [isMobileOrReduced]);

  return (
    <div className="lp-container">
      {/* 1. NAV */}
      <nav className="lp-nav">
        <div className="lp-nav-left">
          <div className="brand" style={{ gap: '8px', padding: 0 }}>
            <div className="brand-mark">M</div>
            <div><strong>MetGo</strong></div>
          </div>
          <div className="lp-nav-links hide-mobile">
            <a href="#problem">The Problem</a>
            <a href="#how-it-works">Pipeline</a>
            <a href="#digital-twin">Try It Live</a>
            <a href="#built-different">Architecture</a>
          </div>
        </div>
        <div className="lp-nav-right">
          <Link to="/dashboard" className="lp-btn-primary">Open Dashboard</Link>
        </div>
      </nav>

      {/* 2. HERO */}
      <header className="lp-hero">
        {!isMobileOrReduced ? (
          <MeshGradient 
            colors={['#0b0e14', '#12161f', '#2f7dfa', '#1a3a66']} 
            distortion={0.4} 
            swirl={0.2} 
            speed={0.1} 
            style={{ position: 'absolute', inset: 0, zIndex: 0 }} 
          />
        ) : (
          <div className="lp-hero-bg"></div>
        )}
        
        {/* Custom SVG Train Background */}
        <div className="lp-hero-svg-wrapper">
          <svg viewBox="0 0 1000 400" preserveAspectRatio="xMidYMid slice" className="lp-hero-train-svg">
            {/* The sweeping rail path */}
            <path id="hero-rail" d="M 0,300 Q 400,300 600,200 T 1100,50" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
            
            {!isMobileOrReduced && (
              <g ref={trainRef} className="hero-train-group">
                {/* Glow / Motion Blur */}
                <rect x="-40" y="-15" width="180" height="30" fill="var(--color-accent)" filter="blur(25px)" opacity="0.3" />
                
                {/* Coaches (3 Alstom Metropolis coaches) */}
                <rect x="-40" y="-12" width="45" height="24" rx="4" fill="var(--color-surface-raised)" stroke="var(--color-border-strong)" strokeWidth="1"/>
                <rect x="10" y="-12" width="45" height="24" rx="4" fill="var(--color-surface-raised)" stroke="var(--color-border-strong)" strokeWidth="1"/>
                <path d="M 60,-12 L 95,-12 Q 105,-12 105,0 Q 105,12 95,12 L 60,12 Z" fill="var(--color-surface-raised)" stroke="var(--color-border-strong)" strokeWidth="1" />
                
                {/* Windows */}
                <rect x="-35" y="-6" width="35" height="8" rx="2" fill="var(--color-bg)" />
                <rect x="15" y="-6" width="35" height="8" rx="2" fill="var(--color-bg)" />
                <rect x="65" y="-6" width="25" height="8" rx="2" fill="var(--color-bg)" />
                
                {/* Accents */}
                <line x1="90" y1="-12" x2="90" y2="12" stroke="var(--color-accent)" strokeWidth="1.5" />
                <circle cx="102" cy="6" r="2" fill="var(--color-signal-red)" />
                <circle cx="102" cy="-6" r="2" fill="var(--color-signal-red)" />
              </g>
            )}
          </svg>
        </div>

        <motion.div className="lp-hero-content" style={{ y: heroY }}>
          <span className="lp-eyebrow-hero">Kochi Metro Operations Suite</span>
          <h1 className="lp-hero-headline">Plan every induction with certainty.</h1>
          <p className="lp-hero-subhead">
            AI-driven nightly induction planning for Kochi Metro. Replace manual spreadsheet planning with constraint-based optimization that guarantees safety and operational goals.
          </p>
          <div className="lp-hero-actions">
            <MagneticButton>
              <Link to="/dashboard" className="lp-btn-primary lp-btn-large">Open Operations Dashboard →</Link>
            </MagneticButton>
            <MagneticButton>
              <a href="#how-it-works" className="lp-btn-secondary lp-btn-large">Explore the Pipeline</a>
            </MagneticButton>
          </div>
          <div className="lp-trust-line">
            <span>Built for Kochi Metro Rail Limited (KMRL)</span>
          </div>
        </motion.div>
      </header>

      {/* 3. PROBLEM FRAMING (The Human Stakes) */}
      <section id="problem" className="lp-problem">
        <div className="lp-problem-grid">
          <div className="lp-problem-text">
            <h2>The stakes of a single night.</h2>
            <p>Every night, Kochi Metro must decide which of its 25 Alstom Metropolis trainsets go into passenger service, standby, maintenance, or cleaning. A poorly planned fleet disrupts the 8-minute headway, affecting over 100,000 daily riders.</p>
            <p>Today, these decisions rely on spreadsheets and institutional experience. MetGo mathematically guarantees these decisions in seconds, ensuring no safety rule is ever silently violated.</p>
          </div>
          <div className="lp-problem-stats">
            <Metric label="Daily Riders" value={100000} prefix="+" tone="blue" />
            <Metric label="Trainsets" value={25} tone="green" />
            <Metric label="Minute Headway" value={8} tone="pink" />
          </div>
        </div>
      </section>

      <NetworkMap />

      {/* 4. PIPELINE SECTIONS (Railway Pattern) */}
      <div id="how-it-works" className="lp-pipeline-wrapper" ref={pipelineRef}>
        <div className="pipeline-container">
          
          {/* Continuous Global Rail */}
          <div className="global-rail-col">
            <div className="global-rail-base"></div>
            <div className="global-rail-fill"></div>
            <div className="global-rail-nodes">
              {[0, 1, 2, 3, 4].map(i => <div key={i} className="global-rail-node"></div>)}
            </div>
            <div className="global-rail-train">
              <svg width="24" height="60" viewBox="0 0 24 60" fill="none">
                <rect x="2" y="2" width="20" height="56" rx="10" fill="var(--rail-color)" opacity="0.4" filter="blur(4px)" />
                <rect x="4" y="4" width="16" height="52" rx="8" fill="#121821" stroke="var(--rail-color)" strokeWidth="2"/>
                <path d="M 6 12 Q 12 6 18 12 L 18 16 L 6 16 Z" fill="#06080a" />
                <path d="M 6 48 Q 12 54 18 48 L 18 44 L 6 44 Z" fill="#06080a" />
                <circle cx="8" cy="52" r="1.5" fill="var(--color-signal-red)" />
                <circle cx="16" cy="52" r="1.5" fill="var(--color-signal-red)" />
                <circle cx="8" cy="8" r="1.5" fill="#fff" />
                <circle cx="16" cy="8" r="1.5" fill="#fff" />
                <line x1="12" y1="20" x2="12" y2="40" stroke="var(--rail-color)" strokeWidth="1" strokeDasharray="2 2" />
              </svg>
            </div>
          </div>

          {/* Pipeline Content Slider */}
          <div className="pipeline-content-slider">
            {[
          {
            id: 'ingest',
            num: '01 / INGEST',
            title: 'Every constraint, modeled exactly.',
            desc: "Fitness certificates, open job cards, and yard stabling geometry aren't guidelines here — they're hard constraints in a CP-SAT solver. If a train shouldn't run, the model won't let it, full stop. No manual override can silently violate a safety rule.",
            colorVar: 'var(--color-pipeline-ingest)',
            features: [
              { title: 'Fitness Certificates', desc: 'Trains without a valid certificate are excluded before optimization begins.' },
              { title: 'Open Job Cards', desc: 'Critical maintenance work routes a train directly to the depot.' }
            ],
            tech: 'FastAPI · PostgreSQL · TimescaleDB',
            RightContent: () => (
              <VignettePatternA 
                topLabel="Raw Fleet Data"
                bottomLabel="Solver Model"
                pillIcon="✓"
                pillText="Constraint Check · Valid"
                colorVar="var(--color-pipeline-ingest)"
              />
            )
          },
          {
            id: 'optimize',
            num: '02 / OPTIMIZE',
            title: 'Balance operational goals.',
            desc: "While hard constraints guarantee safety, soft constraints and weight-tuning minimize unnecessary shunting moves and balance fleet mileage automatically over time. The solver resolves in seconds, not hours.",
            colorVar: 'var(--color-pipeline-optimize)',
            features: [
              { title: 'Mileage Balancing', desc: 'Prioritizes trains with lower mileage for active service.' },
              { title: 'Shunt Minimization', desc: 'Avoids moving trains deep in the yard unless absolutely necessary.' }
            ],
            tech: 'Google OR-Tools CP-SAT · Python',
            RightContent: () => (
              <VignettePatternA 
                topLabel="Objective Weights"
                bottomLabel="Optimized Plan"
                pillIcon="⟳"
                pillText="Balancing · Optimal"
                colorVar="var(--color-pipeline-optimize)"
              />
            )
          },
          {
            id: 'explain',
            num: '03 / EXPLAIN',
            title: 'Understand every decision.',
            desc: "Black-box AI is unacceptable for transit operations. The explainability engine translates complex solver logic into plain-English reasoning per train, bridging the gap between math and the human operator.",
            colorVar: 'var(--color-pipeline-explain)',
            features: [
              { title: 'Natural Language', desc: 'Query exactly why a train was held back or assigned to maintenance.' },
              { title: 'Constraint Tracing', desc: 'Trace the exact hard or soft constraint that drove the assignment.' }
            ],
            tech: 'Explainability Engine · Python',
            RightContent: () => (
              <VignettePatternC colorVar="var(--color-pipeline-explain)" />
            )
          },
          {
            id: 'simulate',
            num: '04 / SIMULATE',
            title: 'Prepare for disruptions.',
            desc: "The night doesn't always go as planned. Use the What-If Simulator to trigger async re-planning when unexpected breakdowns or manual overrides occur, previewing the cascading effects instantly.",
            colorVar: 'var(--color-pipeline-simulate)',
            features: [
              { title: 'Live Overrides', desc: 'Force breakdowns or maintenance and see the new induction plan.' },
              { title: 'Async Queue', desc: 'Heavy re-planning tasks are processed asynchronously without blocking UI.' }
            ],
            tech: 'Redis · Celery',
            RightContent: () => (
              <VignettePatternA 
                topLabel="Manual Override (T12)"
                bottomLabel="Async Plan Rendered"
                pillIcon="⏳"
                pillText={["Processing What-If", "Validating Graph", "Complete"]}
                colorVar="var(--color-pipeline-simulate)"
              />
            )
          },
          {
            id: 'operate',
            num: '05 / OPERATE',
            title: 'Take control of the yard.',
            desc: "The operations dashboard isn't just a static report; it's a live operational digital twin for the night crew, providing instant visibility into stabling layouts and required shunting movements.",
            colorVar: 'var(--color-pipeline-operate)',
            features: [
              { title: 'Live Ops Dashboard', desc: 'Track shunting movements and train statuses in real-time.' },
              { title: 'Human-in-the-Loop', desc: 'The system recommends the plan; the KMRL operator remains the final decision-maker.' }
            ],
            tech: 'React · Neo4j',
            RightContent: () => (
              <VignettePatternB 
                cards={[
                  { id: 'T11', status: 'Online' },
                  { id: 'T04', status: 'Online' },
                  { id: 'T01', status: 'Online' }
                ]}
                colorVar="var(--color-pipeline-operate)"
              />
            )
          }
        ].map((step) => (
          <section key={step.id} className="pipeline-section" style={{ '--section-accent': step.colorVar }}>
            {/* Middle Content */}
            <div className="pipeline-content-col">
                <div className="pipeline-badge">{step.num}</div>
                <h2 className="pipeline-headline">{step.title}</h2>
                <p className="pipeline-desc">{step.desc}</p>
                <a href="#" className="pipeline-learn-more">Learn more &rarr;</a>
                
                <hr className="pipeline-divider" />
                <div className="pipeline-features">
                  <div className="pipeline-feature-row">
                    <div className="pf-icon"></div>
                    <div>
                      <strong>{step.features[0].title}</strong>
                      <span>{step.features[0].desc}</span>
                    </div>
                  </div>
                  <hr className="pipeline-divider" />
                  <div className="pipeline-feature-row">
                    <div className="pf-icon"></div>
                    <div>
                      <strong>{step.features[1].title}</strong>
                      <span>{step.features[1].desc}</span>
                    </div>
                  </div>
                </div>
                <hr className="pipeline-divider" />
                
                <div className="pipeline-tech-row">
                  <span className="tech-label">Built with</span>
                  <div className="tech-tags">{step.tech}</div>
                </div>
              </div>

              {/* Right Visual Panel */}
              <div className="pipeline-visual-col">
                <div className="pipeline-ambient-glow"></div>
                <div className="pipeline-visual-card">
                  <step.RightContent />
                </div>
              </div>
          </section>
        ))}
        </div>
      </div>
    </div>

      {/* 5. TRY IT LIVE (Interactive Demo) */}
      <section id="digital-twin" className="lp-dt-section">
        <div className="lp-dt-header">
          <h2>Try It Live</h2>
          <p>Click a train to simulate a breakdown and watch the async queue handle reassignment instantly.</p>
        </div>
        <div className="lp-dt-preview-wrapper" style={{ padding: '40px', background: 'var(--color-surface)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <MiniDemo />
        </div>
      </section>

      {/* 6. BUILT DIFFERENT (Technical Credibility Bento Grid) */}
      <section id="built-different" className="lp-bento-section">
        <div className="lp-section-title">
          <h2>Engineered for Operations</h2>
          <p>Not a heuristic. Not a generic LLM. True mathematical optimization.</p>
        </div>
        <div className="lp-bento-grid">
          <SpotlightCard className="lp-bento-card bento-large">
            <div className="bento-mockup">
              <div className="mock-code-line"><span style={{color: 'var(--color-signal-amber)'}}>minimize</span> shunting_moves</div>
              <div className="mock-code-line"><span style={{color: 'var(--color-signal-amber)'}}>subject to</span></div>
              <div className="mock-code-line" style={{paddingLeft: '16px'}}>fitness_validity(T) == <span style={{color: 'var(--color-signal-green)'}}>True</span></div>
              <div className="mock-code-line" style={{paddingLeft: '16px'}}>stabling_geometry(Y) == <span style={{color: 'var(--color-signal-green)'}}>Valid</span></div>
              <div className="mock-node-link">
                 <div className="mock-node filled"></div><div className="mock-link"></div><div className="mock-node hollow"></div>
              </div>
            </div>
            <div className="bento-text">
              <h3>CP-SAT Optimization</h3>
              <p>MetGo uses Google OR-Tools Constraint Programming (CP-SAT) to traverse millions of possible fleet combinations. Unlike heuristics that guess, CP-SAT proves optimality or impossibility.</p>
            </div>
          </SpotlightCard>
          <SpotlightCard className="lp-bento-card bento-card-2">
            <h3>Explainability by Design</h3>
            <p>Every decision is logged into a Neo4j knowledge graph, allowing operators to ask "why" and receive concrete constraint-based answers.</p>
          </SpotlightCard>
          <SpotlightCard className="lp-bento-card bento-card-3">
            <h3>Async Re-planning</h3>
            <p>Heavy what-if scenarios are delegated to Redis and Celery, ensuring the operations desk never freezes while waiting for a plan.</p>
          </SpotlightCard>
          <SpotlightCard className="lp-bento-card bento-card-4">
            <h3>Yard Graph</h3>
            <p>Stabling geometry is strictly modeled as a directed graph, ensuring trains aren't blocked by one another during morning dispatch.</p>
          </SpotlightCard>
        </div>
      </section>

      {/* 7. REAL-WORLD GROUNDING */}
      <section className="lp-grounding">
        <div className="lp-grounding-content">
          <h2>A metro like no other.</h2>
          <p>
            Kochi Metro operates 25 Alstom Metropolis trainsets christened after India's sacred rivers (Krishna, Nila, Periyar, Ganga), powered by a 5.389 MWp solar microgrid across Muttom Depot and 25 stations with 100% Kudumbashree-managed station facilities. MetGo brings the same precision and sustainability to its overnight induction planning.
          </p>
        </div>
      </section>

      {/* 8. TECH STACK MARQUEE */}
      <section className="lp-marquee-section">
        <div className="lp-marquee">
          <div className="lp-marquee-content">
            <span>FastAPI</span><span className="dot">•</span>
            <span>PostgreSQL</span><span className="dot">•</span>
            <span>TimescaleDB</span><span className="dot">•</span>
            <span>Neo4j</span><span className="dot">•</span>
            <span>Redis</span><span className="dot">•</span>
            <span>Celery</span><span className="dot">•</span>
            <span>OR-Tools</span><span className="dot">•</span>
            <span>React</span><span className="dot">•</span>
            {/* Duplicate for infinite scroll */}
            <span>FastAPI</span><span className="dot">•</span>
            <span>PostgreSQL</span><span className="dot">•</span>
            <span>TimescaleDB</span><span className="dot">•</span>
            <span>Neo4j</span><span className="dot">•</span>
            <span>Redis</span><span className="dot">•</span>
            <span>Celery</span><span className="dot">•</span>
            <span>OR-Tools</span><span className="dot">•</span>
            <span>React</span><span className="dot">•</span>
          </div>
        </div>
      </section>

      {/* 9. CLOSING CTA */}
      <section className="lp-closing">
        <div className="lp-closing-content">
          <h2>All Aboard.</h2>
          <p>Experience the operational truth for tonight's induction.</p>
          <MagneticButton>
            <Link to="/dashboard" className="lp-btn-primary lp-btn-large lp-pulse">Open Operations Dashboard</Link>
          </MagneticButton>
        </div>
      </section>

      {/* 10. FOOTER */}
      <footer className="lp-footer">
        <div className="lp-footer-grid">
          <div className="lp-footer-col">
            <div className="brand" style={{ gap: '8px', marginBottom: '16px', padding: 0 }}>
              <div className="brand-mark">M</div>
              <div><strong>MetGo</strong></div>
            </div>
            <p className="lp-footer-sub">Built for Kochi Metro Rail Limited.</p>
          </div>
          <div className="lp-footer-col">
            <strong>Project</strong>
            <a href="#how-it-works">Pipeline</a>
            <a href="#built-different">Architecture</a>
            <a href="#digital-twin">Digital Twin</a>
          </div>
          <div className="lp-footer-col">
            <strong>Team</strong>
            <a href="#">BMSIT&M</a>
            <a href="#">EcoTech Innovators</a>
            <a href="#">GitHub Repository</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
