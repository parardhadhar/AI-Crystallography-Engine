import { useState } from 'react'
import UTIF from 'utif'
import './App.css'
import UploadZone from './components/UploadZone'
import IntroScreen from './components/IntroScreen'
import CanvasAnnotator from './components/CanvasAnnotator'
import AIHelperChat from './components/AIHelperChat'
import ProgressBar from './components/ProgressBar'
import CalibrationModal from './components/CalibrationModal'
import AnalyticsPanel from './components/AnalyticsPanel'
import MorphologyMapOverlay from './components/MorphologyMapOverlay'
import ReportEditor from './components/ReportEditor'
import DiffusionEngine from './components/DiffusionEngine'
import LatticeViewer3D from './components/LatticeViewer3D'
import DatasetTable from './components/DatasetTable'

function App() {
  const [scientistName, setScientistName] = useState(null)
  const [material, setMaterial] = useState('FCC')
  const [gVector, setGVector] = useState('[2,0,0]')
  const [zoneAxis, setZoneAxis] = useState('011')
  const [scale, setScale] = useState('120')
  const [sensitivity, setSensitivity] = useState(0.1)
  const [enableFFT, setEnableFFT] = useState(false)
  const [rotationDeg, setRotationDeg] = useState(60)   // Default: Tecnai F30 φ=60°
  const [showMorphMap, setShowMorphMap] = useState(false)
  const [originalImage, setOriginalImage] = useState(null)
  const [uploadedImage, setUploadedImage] = useState(null)
  const [analyzedImage, setAnalyzedImage] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [results, setResults] = useState(null)
  const [defects, setDefects] = useState([])
  const [activeTab, setActiveTab] = useState('canvas')
  const [showWatermark, setShowWatermark] = useState(true)
  const [agentCommand, setAgentCommand] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)
  const [originalFile, setOriginalFile] = useState(null)
  const [fftDataUrl, setFftDataUrl] = useState(null)
  const [showFftModal, setShowFftModal] = useState(false)

  const handleAgentCommand = (actionStr) => {
    setAgentCommand({ action: actionStr, timestamp: Date.now() })
  }

  // Re-run analysis with current sidebar params on the already-uploaded file
  const reAnalyze = async () => {
    if (!originalFile) return
    await executeUpload(originalFile, {
      material, zoneAxis, gVector, scale, sensitivity,
      enableFFT, rotationDeg
    })
  }

  // Fetch and display FFT spectrum from backend
  const showFFTSpectrum = async () => {
    if (!originalFile) return
    try {
      const fd = new FormData()
      fd.append('file', originalFile)
      const resp = await fetch('http://127.0.0.1:8000/fft_spectrum', { method: 'POST', body: fd })
      const json = await resp.json()
      if (json.fft_data_url) {
        setFftDataUrl(json.fft_data_url)
        setShowFftModal(true)
      }
    } catch (e) {
      alert('FFT failed — is the backend running?')
    }
  }

  const handleModalConfirm = async (config) => {
    setMaterial(config.material)
    setZoneAxis(config.zoneAxis)
    setGVector(config.gVector)
    setScale(config.scale)
    setSensitivity(config.sensitivity)
    setEnableFFT(config.enableFFT)
    setRotationDeg(config.rotationDeg ?? rotationDeg)  // sync from modal
    const file = pendingFile
    setOriginalFile(file)
    setPendingFile(null)
    await executeUpload(file, config)
  }

  const handleGlobalExport = () => {
    if (!results || !originalFile) {
      alert("No active session to export.");
      return;
    }
    const sessionData = {
      scientistName,
      timestamp: new Date().toISOString(),
      parameters: { material, zoneAxis, gVector, scale, sensitivity, enableFFT, rotationDeg },
      results,
      defects
    };
    const blob = new Blob([JSON.stringify(sessionData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TEM_Session_Export_${new Date().getTime()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const executeUpload = async (file, config) => {
    setAnalyzing(true)
    setActiveTab('canvas')

    if (file.name.toLowerCase().endsWith('.tif') || file.name.toLowerCase().endsWith('.tiff')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const buffer = e.target.result
          const ifds = UTIF.decode(buffer)
          UTIF.decodeImage(buffer, ifds[0])
          const rgba = UTIF.toRGBA8(ifds[0])
          const canvas = document.createElement('canvas')
          canvas.width = ifds[0].width
          canvas.height = ifds[0].height
          const ctx = canvas.getContext('2d')
          const imageData = ctx.createImageData(canvas.width, canvas.height)
          imageData.data.set(rgba)
          ctx.putImageData(imageData, 0, 0)
          const imgUrl = canvas.toDataURL('image/png')
          setUploadedImage(imgUrl)
          setOriginalImage(imgUrl)
        } catch (err) {
          console.error('Error parsing TIF:', err)
          alert('Failed to parse TIF image.')
        }
      }
      reader.readAsArrayBuffer(file)
    } else {
      const objUrl = URL.createObjectURL(file)
      setUploadedImage(objUrl)
      setOriginalImage(objUrl)
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('material', config.material)
    formData.append('zoneAxis', config.zoneAxis)
    formData.append('gVector', config.gVector)
    formData.append('scale', config.scale)
    formData.append('sensitivity', config.sensitivity)
    formData.append('enable_fft', config.enableFFT ? 'true' : 'false')
    formData.append('rotationDeg', String(config.rotationDeg))   // NEW: φ

    try {
      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
      const json = await response.json()
      if (json.status === 'success') {
        setResults(json.data)
        setDefects(json.defects || [])
        if (json.image_data_url) setUploadedImage(json.image_data_url)
      }
    } catch (err) {
      console.error('API Error:', err)
      alert('Neural Engine Error. Is the backend server running on port 8000?')
    } finally {
      setAnalyzing(false)
    }
  }

  if (!scientistName) {
    return <IntroScreen onStart={(name) => setScientistName(name)} />
  }

  const tabs = [
    { id: 'canvas', label: '🖼 Canvas Studio' },
    { id: 'results', label: '📊 Analysis & Plots' },
    { id: 'report', label: '📄 Report Builder' },
    { id: 'ai', label: '🤖 AI Assistant' },
    { id: 'lattice', label: '🧊 3D Lattice' },
    { id: 'dataset', label: '🗄 LUT Dataset' },
    { id: 'diffusion', label: '🧬 Diffusion Engine' },
  ]

  return (
    <div className="studio-app">
      {pendingFile && (
        <CalibrationModal
          file={pendingFile}
          onCancel={() => setPendingFile(null)}
          onConfirm={handleModalConfirm}
          initialMaterial={material}
          initialZoneAxis={zoneAxis}
          initialGVector={gVector}
          initialScale={scale}
          initialSensitivity={sensitivity}
          initialFFT={enableFFT}
          initialRotationDeg={rotationDeg}
        />
      )}

      {/* Header */}
      <header className="studio-header">
        <div className="brand-logotype">
          <span>S / </span> TEM Engine
        </div>

        {/* Tab Switcher */}
        <div className="tab-switcher">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`tab-btn ${activeTab === t.id ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {uploadedImage && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={handleGlobalExport}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,0.1)',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.05)'}
              >
                Global Export
              </button>
              <button
                onClick={() => {
                  setUploadedImage(null)
                  setResults(null)
                  setDefects([])
                  setOriginalFile(null)
                  setActiveTab('canvas')
                }}
                style={{
                  background: 'var(--accent-primary)',
                  color: '#fff',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 600
                }}
              >
                Upload New Image
              </button>
            </div>
          )}
          {analyzing
            ? <span className="status-badge status-badge--analyzing">⚙ Extracting physics…</span>
            : <span className="status-badge">{scientistName}</span>}
        </div>
      </header>

      {/* Body */}
      <div className="studio-body">

        {/* ── LEFT CONFIG SIDEBAR (always visible) ── */}
        <aside className="studio-sidebar">
          <div className="sidebar-section">
            <h3 className="sidebar-title">Data Source</h3>
            <UploadZone onUpload={(file) => setPendingFile(file)} isAnalyzing={analyzing} />
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-title">Diffraction Parameters</h3>
            <div className="input-stack">
              <div>
                <label>Crystal System</label>
                <select value={material} onChange={(e) => setMaterial(e.target.value)}>
                  <option value="FCC">FCC (Austenitic)</option>
                  <option value="BCC">BCC (Ferritic)</option>
                </select>
              </div>
              <div>
                <label>Diffraction Vector (g)</label>
                <input type="text" value={gVector} onChange={(e) => setGVector(e.target.value)} />
              </div>
              <div>
                <label>Zone Axis</label>
                <input type="text" value={zoneAxis} onChange={(e) => setZoneAxis(e.target.value)} />
              </div>
              <div>
                <label>Scale Calibration (px/100nm)</label>
                <input type="number" value={scale} onChange={(e) => setScale(e.target.value)} />
              </div>

              {/* ── Instrument Rotation φ (plain number input) ── */}
              <div>
                <label style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <span>Instrument Rotation φ</span>
                  <span style={{ fontSize:'0.78rem', color:'var(--accent-primary)', fontWeight:700 }}>
                    {rotationDeg >= 0 ? '+' : ''}{rotationDeg}°
                  </span>
                </label>
                <input
                  type="number"
                  value={rotationDeg}
                  onChange={(e) => setRotationDeg(Number(e.target.value))}
                  min="-180"
                  max="360"
                  step="1"
                  placeholder="e.g. 32"
                  style={{ fontFamily: 'monospace', letterSpacing: '0.05em' }}
                />
                <div style={{ fontSize:'0.69rem', color:'var(--text-tertiary)', marginTop:'4px', lineHeight:1.4 }}>
                  Diffraction–image rotation for this instrument (degrees).
                </div>
              </div>
              <div>
                <label>Detection Sensitivity</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="range" min="0.01" max="0.5" step="0.01"
                    value={sensitivity}
                    onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)', width: '35px' }}>
                    {sensitivity}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                  Lower = Detects Fainter Defects
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input type="checkbox" id="fftToggle" checked={enableFFT}
                    onChange={(e) => setEnableFFT(e.target.checked)}
                    style={{ width: 'auto', cursor: 'pointer' }}
                  />
                  <label htmlFor="fftToggle" style={{ margin: 0, cursor: 'pointer', color: 'var(--text-primary)' }}>
                    FFT Lattice Suppression
                  </label>
                </div>
              </div>
              {/* Re-Analyze with current sidebar params */}
              {originalFile && (
                <button
                  onClick={reAnalyze}
                  disabled={analyzing}
                  style={{
                    marginTop: '0.5rem',
                    width: '100%',
                    padding: '8px 0',
                    borderRadius: '8px',
                    cursor: analyzing ? 'not-allowed' : 'pointer',
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.35), rgba(139,92,246,0.25))',
                    border: '1px solid rgba(99,102,241,0.5)',
                    color: analyzing ? 'rgba(255,255,255,0.3)' : '#a5b4fc',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                    transition: 'all 0.2s',
                  }}
                >
                  {analyzing ? '⚙ Analyzing…' : '⚡ Re-Analyze'}
                </button>
              )}
              {/* FFT Spectrum Viewer */}
              {originalFile && (
                <button
                  onClick={showFFTSpectrum}
                  style={{
                    marginTop: '0.35rem',
                    width: '100%',
                    padding: '8px 0',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    background: 'rgba(16,185,129,0.1)',
                    border: '1px solid rgba(16,185,129,0.3)',
                    color: '#34d399',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                    transition: 'all 0.2s',
                  }}
                >
                  🔭 View Reciprocal Lattice (FFT)
                </button>
              )}
            </div>
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-title">Export Settings</h3>
            <div className="input-stack">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input type="checkbox" id="watermarkToggle" checked={showWatermark}
                  onChange={(e) => setShowWatermark(e.target.checked)}
                  style={{ width: 'auto', cursor: 'pointer' }}
                />
                <label htmlFor="watermarkToggle" style={{ margin: 0, cursor: 'pointer', color: 'var(--text-primary)', fontSize: '0.8rem' }}>
                  Append "{scientistName}" watermark
                </label>
              </div>
            </div>
          </div>

          {/* Colour Legend */}
          <div className="sidebar-section">
            <h3 className="sidebar-title">Colour Legend</h3>
            <div className="legend-list">
              <div className="legend-item"><span className="legend-dot" style={{ background: '#ff69b4' }} />Perfect (FCC 1/2&lt;110&gt;) / BCC &lt;100&gt;</div>
              <div className="legend-item"><span className="legend-dot" style={{ background: '#00ffff' }} />Faulted (FCC 1/3&lt;111&gt;) / BCC 1/2&lt;111&gt;</div>
              <div className="legend-item"><span className="legend-dot" style={{ background: '#ffe600' }} />Edge-On Loops (any family)</div>
              <div className="legend-item"><span className="legend-dot" style={{ background: '#777' }} />Ambiguous / Unknown</div>
            </div>
          </div>


          {/* Morphology Map toggle */}
          <div className="sidebar-section">
            <h3 className="sidebar-title">Morphology Map</h3>
            <button
              onClick={() => setShowMorphMap(v => !v)}
              style={{
                width:'100%', padding:'7px 0', borderRadius:'8px', cursor:'pointer',
                background: showMorphMap ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.05)',
                border: '1px solid ' + (showMorphMap ? '#6366f1' : 'rgba(255,255,255,0.1)'),
                color: showMorphMap ? '#a5b4fc' : 'var(--text-secondary)',
                fontSize:'0.8rem', fontWeight:600, transition:'all 0.2s'
              }}
            >
              {showMorphMap ? '🗺 Hide Reference Map' : '🗺 Show Reference Map'}
            </button>
            <div style={{ fontSize:'0.68rem', color:'var(--text-tertiary)', marginTop:'5px', lineHeight:1.4 }}>
              Interactive crystallographic reference overlaid on the image.
            </div>
          </div>
        </aside>

        {/* ── TAB CONTENT AREA ── */}
        <main className="studio-main">

          {/* CANVAS TAB */}
          {activeTab === 'canvas' && (
            <div className="tab-panel">
              {analyzing && <ProgressBar />}
              {uploadedImage ? (
                <div className="canvas-full" style={{ position:'relative' }}>
                  <CanvasAnnotator
                    imageUrl={uploadedImage}
                    scale={scale}
                    showWatermark={showWatermark}
                    watermarkText={`Work done by ${scientistName}`}
                    agentCommand={agentCommand}
                    rawFile={originalFile}
                    onSnapshotGenerated={(dataUrl) => setAnalyzedImage(dataUrl)}
                  />
                  {showMorphMap && (
                    <MorphologyMapOverlay
                      rotationDeg={rotationDeg}
                      gVector={gVector}
                      zoneAxis={zoneAxis}
                      material={material}
                      defects={defects}
                    />
                  )}
                </div>
              ) : (
                <div className="canvas-empty">
                  <div style={{ fontSize: '4rem' }}>🔬</div>
                  <h3>No Micrograph Loaded</h3>
                  <p>Upload a High-Resolution TEM Micrograph to begin</p>
                </div>
              )}
            </div>
          )}
          {/* RESULTS / PLOTS TAB */}
          {activeTab === 'results' && (
            <div className="tab-panel tab-panel--scroll">
              <AnalyticsPanel results={results} defects={defects} />
            </div>
          )}

          {/* AI ASSISTANT TAB — always mounted, hidden via CSS to preserve state */}
          <div className="tab-panel tab-panel--chat" style={{ display: activeTab === 'ai' ? 'flex' : 'none' }}>
            <AIHelperChat
              contextData={results}
              scientistName={scientistName}
              onAgentCommand={handleAgentCommand}
              material={material}
              gVector={gVector}
              zoneAxis={zoneAxis}
              defects={defects}
            />
          </div>

          {/* REPORT BUILDER TAB */}
          {activeTab === 'report' && (
            <div className="tab-panel tab-panel--scroll" style={{ padding: 0 }}>
              <ReportEditor
                originalImage={originalImage}
                analyzedImage={analyzedImage}
                defects={defects}
                scientistName={scientistName}
                material={material}
                zoneAxis={zoneAxis}
                gVector={gVector}
                scale={scale}
                rotationDeg={rotationDeg}
              />
            </div>
          )}

          {/* 3D LATTICE VIEWER TAB */}
          {activeTab === 'lattice' && (
            <div className="tab-panel" style={{ padding: 0, overflow: 'hidden' }}>
              <LatticeViewer3D material={material} />
            </div>
          )}

          {/* LUT DATASET TABLE TAB */}
          {activeTab === 'dataset' && (
            <div className="tab-panel tab-panel--scroll" style={{ padding: '24px' }}>
              <DatasetTable />
            </div>
          )}

          {/* DIFFUSION ENGINE TAB */}
          {activeTab === 'diffusion' && (
            <div className="tab-panel tab-panel--scroll" style={{ padding: 0 }}>
              <DiffusionEngine 
                scientistName={scientistName} 
                gVector={gVector} 
                zoneAxis={zoneAxis} 
              />
            </div>
          )}
        </main>
      </div>

      {/* ── FFT Spectrum Modal ── */}
      {showFftModal && fftDataUrl && (
        <div
          onClick={() => setShowFftModal(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 9000,
            background: 'rgba(0,0,0,0.85)',
            backdropFilter: 'blur(6px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#0d0d14',
              border: '1px solid rgba(16,185,129,0.35)',
              borderRadius: '16px',
              padding: '20px',
              maxWidth: '720px',
              width: '90vw',
              boxShadow: '0 0 60px rgba(16,185,129,0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div>
                <h3 style={{ margin: 0, color: '#34d399', fontSize: '0.95rem', fontWeight: 700 }}>
                  🔭 Reciprocal Lattice — FFT Power Spectrum
                </h3>
                <p style={{ margin: '4px 0 0', color: 'rgba(255,255,255,0.35)', fontSize: '0.7rem' }}>
                  Frequency-domain representation · Spots = periodic lattice planes · INFERNO colormap
                </p>
              </div>
              <button
                onClick={() => setShowFftModal(false)}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  color: 'rgba(255,255,255,0.5)',
                  width: '30px', height: '30px',
                  cursor: 'pointer', fontSize: '14px',
                }}
              >✕</button>
            </div>
            <img
              src={fftDataUrl}
              alt="FFT Spectrum"
              style={{ width: '100%', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.07)' }}
            />
            <div style={{ marginTop: '10px', fontSize: '0.68rem', color: 'rgba(255,255,255,0.25)', textAlign: 'center' }}>
              Click anywhere outside to close
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

