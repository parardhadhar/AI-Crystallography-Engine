/**
 * MorphologyMapOverlay.jsx — FULLY DYNAMIC VERSION
 *
 * Replaces the old hardcoded FCC [011] diagram with a real-time crystallographic
 * simulator. All loop shapes and visibility states are computed from dot products:
 *   • g · b  → Visibility (zero = invisible)
 *   • |B · n| / (|B||n|) → cos(θ) → morphology (0 = edge-on line, >0 = ellipse)
 *
 * Works for both FCC and BCC with any zone axis and g-vector.
 * The whole diagram rotates by the instrument calibration angle φ.
 */

import { useMemo, useState, useRef, useEffect } from 'react'
import './MorphologyMapOverlay.css'

// ── Crystallographic Dictionaries ─────────────────────────────────────────────
const FCC_VARIANTS = {
  Faulted: [
    { n: [1,1,1],  b: [1,1,1]  },
    { n: [-1,1,1], b: [-1,1,1] },
    { n: [1,-1,1], b: [1,-1,1] },
    { n: [1,1,-1], b: [1,1,-1] },
  ],
  Perfect: [
    { n: [1,1,0],  b: [1,1,0]  },
    { n: [-1,1,0], b: [-1,1,0] },
    { n: [1,0,1],  b: [1,0,1]  },
    { n: [-1,0,1], b: [-1,0,1] },
    { n: [0,1,1],  b: [0,1,1]  },
    { n: [0,-1,1], b: [0,-1,1] },
  ],
}

const BCC_VARIANTS = {
  '1/2<111>': [
    { n: [1,1,1],  b: [1,1,1]  },
    { n: [-1,1,1], b: [-1,1,1] },
    { n: [1,-1,1], b: [1,-1,1] },
    { n: [1,1,-1], b: [1,1,-1] },
  ],
  '<100>': [
    { n: [1,0,0], b: [1,0,0] },
    { n: [0,1,0], b: [0,1,0] },
    { n: [0,0,1], b: [0,0,1] },
  ],
}

// ── Math helpers ──────────────────────────────────────────────────────────────
const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
const norm = (v) => Math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

function parseVector(str) {
  try {
    const s = String(str).trim()
    // Handle '011' format
    if (/^\d{3}$/.test(s)) return [+s[0], +s[1], +s[2]]
    const clean = s.replace(/[[\]()]/g, '')
    const parts = clean.split(',').map(Number)
    if (parts.length === 3 && parts.every(n => !isNaN(n))) return parts
  } catch {}
  return [0, 1, 1]
}

// Compute the 2-D projection direction of a loop when viewed along B
// Returns angle in degrees (0 = right, CCW positive)
function loopProjectionAngle(B, n) {
  // The "direction" a loop projects as in the image plane is perpendicular to (B × n)
  // projected into the image plane. For a simple first approximation:
  // The intersection line of the loop plane (normal n) with the image plane (normal B) is:
  //   direction = B × n
  const Bv = B, nv = n
  const crossX = Bv[1]*nv[2] - Bv[2]*nv[1]
  const crossY = Bv[2]*nv[0] - Bv[0]*nv[2]
  const crossZ = Bv[0]*nv[1] - Bv[1]*nv[0]
  // Project onto image plane — we use the x-y components of B × n
  // (assuming B is approximately along z in the image frame)
  if (Math.abs(crossX) < 1e-9 && Math.abs(crossY) < 1e-9) return 0
  return Math.atan2(-crossY, crossX) * 180 / Math.PI
}

// Evaluate all variants and return structured results for display
function evaluateCrystal(crystal, B, g) {
  const dict = crystal.toUpperCase().includes('FCC') ? FCC_VARIANTS : BCC_VARIANTS
  const B_norm = norm(B)
  const g_norm = norm(g)
  if (B_norm === 0 || g_norm === 0) return []

  const results = []
  for (const [category, variants] of Object.entries(dict)) {
    for (const { n, b } of variants) {
      const g_dot_b = dot(g, b)
      const visible = Math.abs(g_dot_b) > 1e-9

      const n_norm = norm(n)
      const cos_theta = n_norm > 0 ? Math.abs(dot(B, n)) / (B_norm * n_norm) : 1
      const edgeOn = cos_theta < 0.01

      // Color by family
      let color, family
      if (category === 'Faulted') { color = '#00ffff'; family = 'Faulted' }
      else if (category === 'Perfect') { color = '#ff69b4'; family = 'Perfect' }
      else if (category === '1/2<111>') { color = '#00ffff'; family = '1/2<111>' }
      else { color = '#ff69b4'; family = '<100>' }

      // Projection angle in the image (for drawing orientation of ellipse/line)
      const projAngle = loopProjectionAngle(B, n)

      const label = `(${b.map(x => x < 0 ? x.toString().replace('-','̄') : x).join('')})`

      results.push({ category, family, b, n, visible, edgeOn, cos_theta, color, projAngle, label })
    }
  }
  return results
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function MorphologyMapOverlay({ rotationDeg, gVector, zoneAxis, material, defects, isStatic = false }) {
  const phi = Number(rotationDeg) || 0
  const B   = useMemo(() => parseVector(zoneAxis || '011'), [zoneAxis])
  const g   = useMemo(() => parseVector(gVector  || '[1,0,0]'), [gVector])
  const crystal = material || 'FCC'

  // Angle of g in image plane (for arrow direction)
  const gAngle = useMemo(() => {
    // g projected to image: just use h,k for display (ignore l)
    const angle = Math.atan2(-g[1], g[0]) * 180 / Math.PI
    return angle + phi
  }, [g, phi])

  // Compute all variants
  const variants = useMemo(() => evaluateCrystal(crystal, B, g), [crystal, B, g])

  // Layout: place visible variants around the circle, edge-on near center
  const visibleVariants = variants.filter(v => v.visible)
  const invisibleVariants = variants.filter(v => !v.visible)

  // Spread visible variants evenly around the diagram
  const placed = useMemo(() => {
    const placed = []
    const count = visibleVariants.length
    visibleVariants.forEach((v, i) => {
      const spreadAngle = (360 / Math.max(count, 1)) * i - 90
      const r = v.edgeOn ? 55 : 85
      placed.push({ ...v, spreadAngle, r })
    })
    return placed
  }, [visibleVariants])

  // SVG params
  const cx = 155, cy = 155, mapR = 120

  // Dragging
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0, ox: 0, oy: 0 })

  const handlePointerDown = (e) => {
    if (isStatic) return
    setIsDragging(true)
    dragStart.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y }
  }

  useEffect(() => {
    if (!isDragging || isStatic) return
    const move = (e) => setOffset({ x: dragStart.current.ox + e.clientX - dragStart.current.x, y: dragStart.current.oy + e.clientY - dragStart.current.y })
    const up   = () => setIsDragging(false)
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up) }
  }, [isDragging, isStatic])

  // Summary stats
  const edgeOnLoops = placed.filter(v => v.edgeOn)
  const inclinedLoops = placed.filter(v => !v.edgeOn)

  return (
    <div
      className={`morph-overlay ${isDragging ? 'dragging' : ''} ${isStatic ? 'static-mode' : ''}`}
      style={{ transform: isStatic ? 'none' : `translate(${offset.x}px, ${offset.y}px)` }}
    >
      {/* Title */}
      <div
        className="morph-overlay__title"
        onPointerDown={handlePointerDown}
        style={{ cursor: isStatic ? 'default' : (isDragging ? 'grabbing' : 'grab'), width: '100%', paddingBottom: '4px' }}
      >
        {!isStatic && <span style={{ opacity: 0.4, marginRight: '4px', fontSize:'0.7rem' }}>⋮⋮</span>}
        Morphological Reference Map
        <span className="morph-overlay__phi">φ = {phi >= 0 ? '+' : ''}{phi}°</span>
      </div>

      {/* SVG diagram */}
      <svg className="morph-overlay__svg" viewBox="0 0 310 310" width="310" height="310">
        <defs>
          <radialGradient id="bgGradDyn" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#1e1b4b" stopOpacity="0.9"/>
            <stop offset="100%" stopColor="#0f172a" stopOpacity="0.98"/>
          </radialGradient>
          <filter id="glowDyn">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Background */}
        <circle cx={cx} cy={cy} r={mapR + 35} fill="url(#bgGradDyn)"/>
        <circle cx={cx} cy={cy} r={mapR} fill="none" stroke="rgba(99,102,241,0.25)" strokeWidth="1"/>
        <circle cx={cx} cy={cy} r={mapR * 0.5} fill="none" stroke="rgba(99,102,241,0.1)" strokeWidth="1" strokeDasharray="4,4"/>

        {/* Cross-hairs */}
        <line x1={cx-mapR-25} y1={cy} x2={cx+mapR+25} y2={cy} stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
        <line x1={cx} y1={cy-mapR-25} x2={cx} y2={cy+mapR+25} stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>

        {/* ── Rotating diagram group (rotated by φ) ── */}
        <g transform={`rotate(${-phi}, ${cx}, ${cy})`}>

          {/* Invisible variants - small grey dots around edge */}
          {invisibleVariants.map((v, i) => {
            const a = ((360 / Math.max(invisibleVariants.length, 1)) * i - 90) * Math.PI / 180
            const x = cx + (mapR + 18) * Math.cos(a)
            const y = cy + (mapR + 18) * Math.sin(a)
            return (
              <g key={`inv-${i}`}>
                <circle cx={x} cy={y} r="4" fill="none" stroke="rgba(100,116,139,0.4)" strokeWidth="1" strokeDasharray="2,2"/>
                <text x={x} y={y+11} textAnchor="middle" fill="rgba(100,116,139,0.5)" fontSize="7">g·b=0</text>
              </g>
            )
          })}

          {/* Visible variants */}
          {placed.map((v, i) => {
            const rad = v.spreadAngle * Math.PI / 180
            const px = cx + v.r * Math.cos(rad)
            const py = cy + v.r * Math.sin(rad)
            const projRad = (v.projAngle) * Math.PI / 180

            if (v.edgeOn) {
              // Edge-on: draw as a straight line oriented by B × n projection
              const lineLen = 28
              const dx = (lineLen / 2) * Math.cos(projRad)
              const dy = (lineLen / 2) * Math.sin(projRad)
              return (
                <g key={`v-${i}`}>
                  <line
                    x1={px - dx} y1={py - dy} x2={px + dx} y2={py + dy}
                    stroke={v.color} strokeWidth="3.5" strokeLinecap="round"
                    strokeDasharray={v.family === 'Faulted' || v.family === '1/2<111>' ? '6,3' : 'none'}
                  />
                  <text x={px + 20 * Math.cos(rad)} y={py + 20 * Math.sin(rad)}
                    textAnchor="middle" dominantBaseline="central"
                    fill={v.color} fontSize="9" fontWeight="bold" opacity="0.85"
                  >
                    {v.family}
                  </text>
                  <text x={px - 20 * Math.cos(rad)} y={py - 20 * Math.sin(rad)}
                    textAnchor="middle" dominantBaseline="central"
                    fill={v.color} fontSize="8" opacity="0.6"
                  >
                    Edge-On
                  </text>
                </g>
              )
            } else {
              // Inclined: draw as ellipse with 3D-like styling
              // Aspect ratio from cos_theta
              const ry = Math.max(4, 14 * v.cos_theta)
              const gradientId = `grad-${i}`
              return (
                <g key={`v-${i}`} filter="url(#glowDyn)">
                  <defs>
                    <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor={v.color} stopOpacity="0.9" />
                      <stop offset="100%" stopColor={v.color} stopOpacity="0.2" />
                    </linearGradient>
                  </defs>
                  <ellipse
                    cx={px} cy={py} rx="18" ry={ry}
                    transform={`rotate(${v.projAngle + 90}, ${px}, ${py})`}
                    fill={`url(#${gradientId})`} stroke={v.color} strokeWidth="2" opacity="0.95"
                  />
                  <text x={px + 22 * Math.cos(rad)} y={py + 22 * Math.sin(rad)}
                    textAnchor="middle" dominantBaseline="central"
                    fill={v.color} fontSize="9" fontWeight="bold" opacity="0.9"
                  >
                    {v.family}
                  </text>
                </g>
              )
            }
          })}

          {/* Center origin dot */}
          <circle cx={cx} cy={cy} r="3.5" fill="#ffffff" opacity="0.8"/>
          <text x={cx} y={cy + 12} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="8">000</text>
        </g>

        {/* ── g-vector arrow (fixed in image frame, NOT rotated) ── */}
        {(() => {
          const rad = gAngle * Math.PI / 180
          const gLen = mapR * 0.55
          const gx = cx + gLen * Math.cos(rad)
          const gy = cy - gLen * Math.sin(rad)
          return (
            <g filter="url(#glowDyn)">
              <line x1={cx} y1={cy} x2={gx} y2={gy} stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round"/>
              {/* Arrowhead */}
              <polygon
                points={`${gx+8*Math.cos(rad)},${gy-8*Math.sin(rad)} ${gx-7*Math.cos(rad-0.45)},${gy+7*Math.sin(rad-0.45)} ${gx-7*Math.cos(rad+0.45)},${gy+7*Math.sin(rad+0.45)}`}
                fill="#818cf8"
              />
              {/* g label */}
              <text
                x={gx + 18 * Math.cos(rad)} y={gy - 18 * Math.sin(rad)}
                textAnchor="middle" dominantBaseline="central"
                fill="#c7d2fe" fontSize="12" fontWeight="bold" fontFamily="monospace"
              >
                g=[{g.join(',')}]
              </text>
            </g>
          )
        })()}

        {/* Zone axis and crystal label */}
        <text x={cx} y={cy + mapR + 22} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" fontFamily="monospace">
          Zone Axis: [{Array.isArray(B) ? B.join(',') : zoneAxis}]  |  {crystal}
        </text>

        {/* Condition summary at top */}
        <text x={cx} y={18} textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="9" fontFamily="monospace">
          {edgeOnLoops.length} edge-on  ·  {inclinedLoops.length} inclined  ·  {invisibleVariants.length} invisible (g·b=0)
        </text>
      </svg>

      {/* Legend */}
      <div className="morph-overlay__legend">
        <div className="morph-legend-item">
          <svg width="28" height="14" viewBox="0 0 28 14">
            <ellipse cx="14" cy="7" rx="12" ry="6" fill="none" stroke="#ff69b4" strokeWidth="1.5"/>
          </svg>
          <span>Perfect / &lt;100&gt;</span>
        </div>
        <div className="morph-legend-item">
          <svg width="28" height="14" viewBox="0 0 28 14">
            <ellipse cx="14" cy="7" rx="12" ry="4" fill="none" stroke="#00ffff" strokeWidth="1.5" strokeDasharray="4,2"/>
          </svg>
          <span>Faulted / 1/2&lt;111&gt;</span>
        </div>
        <div className="morph-legend-item">
          <svg width="28" height="14" viewBox="0 0 28 14">
            <line x1="2" y1="7" x2="26" y2="7" stroke="#ffffff" strokeWidth="2.5" strokeDasharray="4,3" strokeOpacity="0.5"/>
          </svg>
          <span>g·b=0 (Invisible)</span>
        </div>
      </div>

      {/* Detected loop orientation rose */}
      {defects && defects.length > 0 && (
        <div className="morph-overlay__stats">
          <div className="morph-stat-title">Detected Loop Orientations</div>
          <OrientationRose defects={defects} rotationDeg={phi} gVector={g}/>
        </div>
      )}
    </div>
  )
}

// ── Polar rose chart ──────────────────────────────────────────────────────────
function OrientationRose({ defects, rotationDeg, gVector }) {
  const SIZE = 120, cx = 60, cy = 60, R = 52

  const COLOR_MAP = {
    'Cyan': '#00ffff', 'Pink': '#ff69b4', 'None': '#334155',
  }

  const bins = Array(18).fill(0)
  const binColors = Array(18).fill('#94a3b8')

  defects.forEach(d => {
    if (d.angle_deg == null) return
    let a = ((d.angle_deg % 180) + 180) % 180
    const bi = Math.min(17, Math.floor(a / 10))
    bins[bi]++
    const col = d.ui_color ? (COLOR_MAP[d.ui_color] || '#94a3b8') : '#94a3b8'
    binColors[bi] = col
  })

  const maxBin = Math.max(...bins, 1)

  const petals = bins.flatMap((count, i) => {
    if (count === 0) return []
    const frac = count / maxBin
    const r = R * 0.15 + R * 0.85 * frac
    const aStart = (i * 10) * Math.PI / 180
    const aEnd   = ((i + 1) * 10) * Math.PI / 180
    return [0, Math.PI].map((off, j) => {
      const a1 = aStart + off, a2 = aEnd + off
      const x1 = cx + r * Math.cos(a1), y1 = cy - r * Math.sin(a1)
      const x2 = cx + r * Math.cos(a2), y2 = cy - r * Math.sin(a2)
      return (
        <path key={`${i}-${j}`}
          d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 0 ${x2} ${y2} Z`}
          fill={binColors[i]} fillOpacity="0.55" stroke={binColors[i]} strokeWidth="0.5"
        />
      )
    })
  })

  // g-vector angle in image
  const gAngle = gVector ? Math.atan2(-gVector[1], gVector[0]) * 180 / Math.PI + rotationDeg : rotationDeg
  const gRad = gAngle * Math.PI / 180
  const gx1 = cx + R * Math.cos(gRad), gy1 = cy - R * Math.sin(gRad)
  const gx2 = cx - R * Math.cos(gRad), gy2 = cy + R * Math.sin(gRad)

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'4px' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        {[0.33, 0.66, 1].map(f => (
          <circle key={f} cx={cx} cy={cy} r={R*f} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1"/>
        ))}
        {Array.from({length:18}, (_,i) => {
          const a = (i*10)*Math.PI/180
          return <line key={i} x1={cx+R*0.9*Math.cos(a)} y1={cy-R*0.9*Math.sin(a)} x2={cx+R*Math.cos(a)} y2={cy-R*Math.sin(a)} stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
        })}
        {petals}
        <line x1={gx1} y1={gy1} x2={gx2} y2={gy2} stroke="#818cf8" strokeWidth="1.5" strokeDasharray="4,3" opacity="0.85"/>
        <circle cx={cx} cy={cy} r="3" fill="#6366f1"/>
        <text x={cx+R+3} y={cy+4} fill="rgba(255,255,255,0.25)" fontSize="7">0°</text>
        <text x={cx-3} y={cy-R-3} textAnchor="middle" fill="rgba(255,255,255,0.25)" fontSize="7">90°</text>
      </svg>
      <div style={{ fontSize:'0.63rem', color:'rgba(255,255,255,0.3)', textAlign:'center' }}>
        Petal length = loop count per orientation bin<br/>
        Dashed line = g direction (φ={rotationDeg}°)
      </div>
    </div>
  )
}
