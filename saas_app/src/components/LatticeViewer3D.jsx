import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Line } from '@react-three/drei'
import * as THREE from 'three'
import './LatticeViewer3D.css'

// ── Reusable Atom ─────────────────────────────────────────────────────────────
function Atom({ position, color, radius = 0.13, emissive = false }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshStandardMaterial
        color={color}
        roughness={0.25}
        metalness={0.6}
        emissive={emissive ? color : '#000000'}
        emissiveIntensity={emissive ? 0.3 : 0}
      />
    </mesh>
  )
}

// ── Arrow (Burgers vector) ────────────────────────────────────────────────────
function Arrow({ start, end, color }) {
  const dir = new THREE.Vector3().subVectors(end, start)
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
  const length = dir.length()
  if (length < 0.001) return null

  const axis = new THREE.Vector3(0, 1, 0)
  const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, dir.clone().normalize())

  return (
    <group>
      <Line points={[start, end]} color={color} lineWidth={2.5} />
      <mesh position={end} quaternion={quaternion}>
        <coneGeometry args={[0.05, 0.15, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
      </mesh>
    </group>
  )
}

// ── Slip Plane (semi-transparent quad) ───────────────────────────────────────
function SlipPlane({ points, color }) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const verts = new Float32Array([
      ...points[0], ...points[1], ...points[2],
      ...points[0], ...points[2], ...points[3],
    ])
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    geo.computeVertexNormals()
    return geo
  }, [points])

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={color} transparent opacity={0.15} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  )
}

// ── FCC Unit Cell ─────────────────────────────────────────────────────────────
function FCCCell() {
  const group = useRef()
  useFrame(({ clock }) => {
    if (group.current) group.current.rotation.y = clock.elapsedTime * 0.12
  })

  // Atom positions — all in [-0.5, 0.5] centred on origin
  const corners = useMemo(() => {
    const pts = []
    for (let x of [-0.5, 0.5]) for (let y of [-0.5, 0.5]) for (let z of [-0.5, 0.5]) pts.push([x, y, z])
    return pts
  }, [])

  const faceCentres = [
    [ 0,    0,   -0.5], [ 0,    0,    0.5],
    [ 0,  -0.5,   0 ], [ 0,   0.5,   0  ],
    [-0.5,  0,    0  ], [ 0.5,  0,    0  ],
  ]

  // Octahedral interstitial (body centre of FCC = octahedral hole)
  const octaHole = [0, 0, 0]

  // Edges
  const edges = useMemo(() => {
    const E = []
    const c = [-0.5, 0.5]
    for (let i of c) for (let j of c) {
      E.push([new THREE.Vector3(i, j, -0.5), new THREE.Vector3(i, j,  0.5)])
      E.push([new THREE.Vector3(i, -0.5, j), new THREE.Vector3(i,  0.5, j)])
      E.push([new THREE.Vector3(-0.5, i, j), new THREE.Vector3( 0.5, i, j)])
    }
    return E
  }, [])

  // Burgers vector: ½[1̄10] — in unit-cell units this is from (-0.5,0.5,0) to (0.5,0,0) rough
  const bStart = new THREE.Vector3(-0.5, 0.5, -0.5)
  const bEnd   = new THREE.Vector3( 0.5, 0,  -0.5)

  // Slip plane (111)
  const slipPts = [
    [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, 0.5], [-0.5, -0.5, 0.5]
  ]

  return (
    <group ref={group}>
      {edges.map((e, i) => <Line key={i} points={e} color="rgba(255,255,255,0.18)" lineWidth={1} />)}
      {corners.map((p, i)     => <Atom key={`c${i}`}  position={p} color="#94a3b8" radius={0.13} />)}
      {faceCentres.map((p, i) => <Atom key={`f${i}`}  position={p} color="#38bdf8" radius={0.11} />)}
      <Atom position={octaHole} color="#f87171" radius={0.075} emissive />

      <SlipPlane points={slipPts} color="#38bdf8" />
      <Arrow start={bStart} end={bEnd} color="#c084fc" />
    </group>
  )
}

// ── BCC Unit Cell ─────────────────────────────────────────────────────────────
function BCCCell() {
  const group = useRef()
  useFrame(({ clock }) => {
    if (group.current) group.current.rotation.y = clock.elapsedTime * 0.12
  })

  const corners = useMemo(() => {
    const pts = []
    for (let x of [-0.5, 0.5]) for (let y of [-0.5, 0.5]) for (let z of [-0.5, 0.5]) pts.push([x, y, z])
    return pts
  }, [])

  const edges = useMemo(() => {
    const E = []
    const c = [-0.5, 0.5]
    for (let i of c) for (let j of c) {
      E.push([new THREE.Vector3(i, j, -0.5), new THREE.Vector3(i, j,  0.5)])
      E.push([new THREE.Vector3(i, -0.5, j), new THREE.Vector3(i,  0.5, j)])
      E.push([new THREE.Vector3(-0.5, i, j), new THREE.Vector3( 0.5, i, j)])
    }
    return E
  }, [])

  // ½⟨111⟩ Burgers vector
  const bStart = new THREE.Vector3(-0.5, -0.5, -0.5)
  const bEnd   = new THREE.Vector3( 0.5,  0.5,  0.5)

  // Slip plane (110)
  const slipPts = [
    [0.5, 0.5, -0.5], [0.5, -0.5, 0.5], [-0.5, -0.5, 0.5], [-0.5, 0.5, -0.5]
  ]

  return (
    <group ref={group}>
      {edges.map((e, i) => <Line key={i} points={e} color="rgba(255,255,255,0.18)" lineWidth={1} />)}
      {corners.map((p, i) => <Atom key={`c${i}`} position={p} color="#94a3b8" radius={0.13} />)}
      <Atom position={[0, 0, 0]} color="#facc15" radius={0.14} emissive />
      {/* Tetrahedral interstitial example */}
      <Atom position={[0.5, 0.25, 0]} color="#f87171" radius={0.065} emissive />

      <SlipPlane points={slipPts} color="#facc15" />
      <Arrow start={bStart} end={bEnd} color="#c084fc" />
    </group>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function LatticeViewer3D({ material = 'FCC' }) {
  const isFCC = material === 'FCC'

  const legend = isFCC ? [
    { color: '#94a3b8', label: 'Corner atoms' },
    { color: '#38bdf8', label: 'Face-centre atoms' },
    { color: '#f87171', label: 'Octahedral interstitial' },
    { color: '#c084fc', label: `Burgers vector b = ½[1̄10]` },
    { color: '#38bdf8', label: '(111) slip plane', plane: true },
  ] : [
    { color: '#94a3b8', label: 'Corner atoms' },
    { color: '#facc15', label: 'Body-centre atom' },
    { color: '#f87171', label: 'Tetrahedral interstitial' },
    { color: '#c084fc', label: 'Burgers vector b = ½[111]' },
    { color: '#facc15', label: '(110) slip plane', plane: true },
  ]

  return (
    <div className="lv-root">
      {/* Header */}
      <div className="lv-head">
        <div>
          <h2 className="lv-title">3D Lattice &amp; Burgers Vector Analyser</h2>
          <p className="lv-subtitle">Drag to rotate · Scroll to zoom · {material} crystal structure</p>
        </div>
        <div className="lv-material-badge">{material}</div>
      </div>

      {/* Canvas */}
      <div className="lv-canvas">
        <Canvas camera={{ position: [2.2, 1.6, 2.2], fov: 42 }} shadows>
          <color attach="background" args={['#080c14']} />

          <ambientLight intensity={0.6} />
          <pointLight position={[3, 3, 3]} intensity={1.2} />
          <pointLight position={[-3, -2, -3]} intensity={0.5} color="#4040ff" />

          <Suspense fallback={null}>
            {isFCC ? <FCCCell /> : <BCCCell />}
          </Suspense>

          <OrbitControls enablePan={false} enableZoom minDistance={1.2} maxDistance={5} />
        </Canvas>
      </div>

      {/* Legend */}
      <div className="lv-legend">
        {legend.map((l, i) => (
          <div key={i} className="lv-legend-item">
            {l.plane ? (
              <span className="lv-legend-plane" style={{ borderColor: l.color }} />
            ) : (
              <span className="lv-legend-dot" style={{ background: l.color }} />
            )}
            <span className="lv-legend-label">{l.label}</span>
          </div>
        ))}
      </div>

      {/* Info panel */}
      <div className="lv-info">
        {isFCC ? (
          <>
            <div className="lv-info-item"><strong>Slip system:</strong> {'{111}⟨110⟩'}</div>
            <div className="lv-info-item"><strong>Burgers vector:</strong> b = ½⟨110⟩, |b| = a/√2</div>
            <div className="lv-info-item"><strong>Stacking:</strong> ABCABC…</div>
          </>
        ) : (
          <>
            <div className="lv-info-item"><strong>Slip system:</strong> {'{110}⟨111⟩'}</div>
            <div className="lv-info-item"><strong>Burgers vector:</strong> b = ½⟨111⟩, |b| = a√3/2</div>
            <div className="lv-info-item"><strong>Stacking:</strong> ABAB…</div>
          </>
        )}
      </div>
    </div>
  )
}
