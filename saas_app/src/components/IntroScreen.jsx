import React, { useEffect, useRef, useState } from 'react'
import './IntroScreen.css'

export default function IntroScreen({ onStart }) {
  const canvasRef = useRef(null)
  const [scientistName, setScientistName] = useState('')
  const [step, setStep] = useState(-1) // -1 is the preloader boot sequence
  const [isExiting, setIsExiting] = useState(false)
  const [bootProgress, setBootProgress] = useState(0)

  useEffect(() => {
    if (step === -1) {
      let progress = 0;
      const interval = setInterval(() => {
        // Random bursts of loading speed to look like real system boot
        progress += Math.floor(Math.random() * 18) + 2;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setTimeout(() => setStep(0), 600); // Brief pause at 100% then reveal
        }
        setBootProgress(progress);
      }, 120);
      return () => clearInterval(interval);
    }
  }, [step])

  useEffect(() => {
    // Superb Dark Theme Particle Animation
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    let animationFrameId
    
    let width = window.innerWidth
    let height = window.innerHeight
    canvas.width = width
    canvas.height = height

    const particles = []
    const particleCount = 100

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 0.5,
        alpha: Math.random() * 0.5 + 0.1
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
      ctx.lineWidth = 1
      const gridSize = 50
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
      }

      particles.forEach((p, i) => {
        p.x += p.vx
        p.y += p.vy

        if (p.x < 0 || p.x > width) p.vx *= -1
        if (p.y < 0 || p.y > height) p.vy *= -1

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`
        ctx.fill()

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j]
          const dx = p.x - p2.x
          const dy = p.y - p2.y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < 100) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - dist / 100)})`
            ctx.stroke()
          }
        }
      })

      animationFrameId = requestAnimationFrame(draw)
    }

    draw()

    const handleResize = () => {
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = width
      canvas.height = height
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  const handleNextStep = () => {
    if (step === 0) {
      // Move from Connect to Identification
      setStep(1)
    } else if (step === 1) {
      // Validate Name and Move to System Online
      if (scientistName.trim() === '') setScientistName('Guest Scientist')
      setStep(2)
    } else if (step === 2) {
      // Move to Manual
      setStep(3)
    } else if (step === 3) {
      // Trigger Netflix cinematic zoom exit
      setIsExiting(true)
      setTimeout(() => {
        onStart(scientistName)
      }, 1000) // Wait 1 second for the zoom animation to finish
    }
  }

  return (
    <div className={`dark-intro-wrapper ${isExiting ? 'netflix-zoom-exit' : ''}`}>
      
      {/* ── AWWWARDS PRELOADER OVERLAY ── */}
      <div className={`awwwards-preloader ${step >= 0 ? 'loaded' : ''}`}>
        <div className="preloader-half top"></div>
        <div className="preloader-half bottom"></div>
        <div className="preloader-content-wrap">
          <div className="preloader-content">
            <div className="preloader-text">NEURAL INITIALIZATION</div>
            <div className="preloader-progress">{bootProgress}%</div>
            <div className="preloader-bar-container">
              <div className="preloader-bar" style={{ width: `${bootProgress}%` }}></div>
            </div>
            <div className="preloader-logs">
              {bootProgress < 30 && <span>Waking AI Cores...</span>}
              {bootProgress >= 30 && bootProgress < 65 && <span>Loading Crystallography LUTs...</span>}
              {bootProgress >= 65 && bootProgress < 100 && <span>Calibrating SAM Visual Models...</span>}
              {bootProgress === 100 && <span className="text-ready">System Ready</span>}
            </div>
          </div>
        </div>
      </div>

      <canvas ref={canvasRef} className="intro-canvas"></canvas>
      
      <div className="dark-intro-content">
        {/* Step 0: Title & Connect */}
        {step === 0 && (
          <div className="step-container animate-in">
            <div className="intro-badge">S / T E M</div>
            <h1 className="intro-main-title" style={{ fontSize: 'clamp(2.5rem, 6vw, 5rem)' }}>
              AI Crystallographic Design
            </h1>
            <p className="intro-subtext">
              High-performance material physics extraction via neural computation.
            </p>
            
            <button className="dark-start-btn" onClick={handleNextStep}>
              <span className="btn-text">CONNECT TO MAINFRAME</span>
              <div className="btn-glow"></div>
            </button>
          </div>
        )}

        {/* Step 1: Identification */}
        {step === 1 && (
          <div className="step-container animate-in">
            <h2 className="intro-main-title" style={{ fontSize: '2.5rem', marginBottom: '2rem' }}>IDENTIFICATION REQUIRED</h2>
            <div className="onboarding-form">
              <input 
                type="text" 
                name="random-name-field"
                className="scientist-input"
                placeholder="Enter Scientist or Organization Name..." 
                value={scientistName}
                onChange={(e) => setScientistName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleNextStep()}
                autoComplete="new-password"
                spellCheck="false"
                autoFocus
              />
              <button className="dark-start-btn" onClick={handleNextStep}>
                <span className="btn-text">VERIFY IDENTITY</span>
                <div className="btn-glow"></div>
              </button>
            </div>
          </div>
        )}

        {/* Step 2: System Online */}
        {step === 2 && (
          <div className="step-container animate-in">
            <h2 className="intro-main-title" style={{ fontSize: '3rem', color: '#10B981' }}>SYSTEM ONLINE</h2>
            <p className="intro-subtext" style={{ fontSize: '1.25rem', color: '#FFFFFF', maxWidth: '600px' }}>
              Welcome, <strong style={{ color: '#10B981' }}>{scientistName}</strong>. 
              <br/><br/>
              Neural link established. <br/>
              <span style={{ color: '#EF4444', fontSize: '0.875rem', letterSpacing: '0.1em', marginTop: '1rem', display: 'inline-block' }}>
                WARNING: High-contrast data extraction ahead. Prolonged session may cause eye strain.
              </span>
            </p>
            
            <button className="dark-start-btn" onClick={handleNextStep} style={{ marginTop: '2rem' }}>
              <span className="btn-text">I AM READY</span>
              <div className="btn-glow"></div>
            </button>
          </div>
        )}

        {/* Step 3: Operating Manual */}
        {step === 3 && (
          <div className="step-container animate-in">
            <h2 className="intro-main-title" style={{ fontSize: '2.5rem' }}>OPERATING MANUAL</h2>
            
            <div className="manual-list">
              <div className="manual-item">
                <span className="manual-num">01</span>
                <div>
                  <h4>Upload Micrograph</h4>
                  <p>Drop high-resolution .TIF or .PNG images into the left-hand data source panel.</p>
                </div>
              </div>
              <div className="manual-item">
                <span className="manual-num">02</span>
                <div>
                  <h4>Calibrate Parameters</h4>
                  <p>Define Crystal System, g-vector, zone axis, and scale calibration.</p>
                </div>
              </div>
              <div className="manual-item">
                <span className="manual-num">03</span>
                <div>
                  <h4>AI Extraction</h4>
                  <p>The neural engine will automatically identify defects and extract Burgers vectors.</p>
                </div>
              </div>
            </div>
            
            <button className="dark-start-btn" onClick={handleNextStep} style={{ marginTop: '3rem' }}>
              <span className="btn-text">INITIALIZE WORKSPACE</span>
              <div className="btn-glow"></div>
            </button>
          </div>
        )}

      </div>
      
      {step === 0 && (
        <div className="made-by-credit animate-in delay-4">
          Made by Parardha Dhar
        </div>
      )}
    </div>
  )
}
