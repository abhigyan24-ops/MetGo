import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import LandingPage from './LandingPage.jsx'

// Lenis smooth scroll — applied to the document root.
// Gives the landing/home view a premium scroll feel.
// We initialize it here and let it run globally; Lenis is smart enough
// not to interfere with non-scrolling views (ops dashboard panels).
async function initLenis() {
  try {
    const { default: Lenis } = await import('lenis')
    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    })
    function raf(time) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)
  } catch {
    // Lenis failed to load — graceful degradation, native scroll still works
  }
}

initLenis()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
