import React, { useState } from 'react';
import './CalibrationModal.css';

export default function CalibrationModal({ 
  file, 
  onCancel, 
  onConfirm,
  initialMaterial = 'FCC',
  initialZoneAxis = '011',
  initialGVector = '[2,0,0]',
  initialScale = '120',
  initialSensitivity = 0.1,
  initialFFT = false,
  initialRotationDeg = 0
}) {
  const [material, setMaterial] = useState(initialMaterial);
  const [zoneAxis, setZoneAxis] = useState(initialZoneAxis);
  const [gVector, setGVector] = useState(initialGVector);
  const [scale, setScale] = useState(initialScale);
  const [sensitivity, setSensitivity] = useState(initialSensitivity);
  const [enableFFT, setEnableFFT] = useState(initialFFT);
  const [rotationDeg, setRotationDeg] = useState(initialRotationDeg);
  const [microscopePreset, setMicroscopePreset] = useState('custom');

  // Microscope rotation presets (documented image-to-diffraction rotation offsets)
  const MICROSCOPE_PRESETS = [
    { id: 'tecnai_f30',   label: 'Thermo Fisher / FEI Tecnai F30 (300 kV)', phi: 60  },
    { id: 'tecnai_f20',   label: 'Thermo Fisher / FEI Tecnai F20 (200 kV)', phi: 90  },
    { id: 'jeol_2100',    label: 'JEOL JEM-2100 (200 kV)',                   phi: 0   },
    { id: 'jeol_2100f',   label: 'JEOL JEM-2100F (200 kV)',                  phi: 7   },
    { id: 'titan_80300',  label: 'Thermo Fisher Titan 80-300 (300 kV)',      phi: 0   },
    { id: 'cm300',        label: 'Philips CM300 (300 kV)',                    phi: 32  },
    { id: 'custom',       label: 'Custom / Manual entry',                     phi: null },
  ];

  const handlePresetChange = (presetId) => {
    setMicroscopePreset(presetId);
    const preset = MICROSCOPE_PRESETS.find(p => p.id === presetId);
    if (preset && preset.phi !== null) {
      setRotationDeg(preset.phi);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({
      material,
      zoneAxis,
      gVector,
      scale,
      sensitivity,
      enableFFT,
      rotationDeg: Number(rotationDeg)
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        
        <div className="modal-header">
          <h2 className="modal-title">Configure Analysis</h2>
          <p className="modal-subtitle">
            Enter the TEM session parameters for <strong>{file?.name}</strong> before launching the Neural Engine.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">

          {/* ── Row 1: Crystal System + Scale ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="modal-input-group">
              <label>Crystal System</label>
              <select value={material} onChange={(e) => setMaterial(e.target.value)}>
                <option value="FCC">FCC (Austenitic Steel / Ni alloys)</option>
                <option value="BCC">BCC (Ferritic Steel / W alloys)</option>
              </select>
            </div>
            <div className="modal-input-group">
              <label>Scale (px per 100 nm)</label>
              <input
                type="number"
                value={scale}
                onChange={(e) => setScale(e.target.value)}
                placeholder="e.g. 120"
                required
              />
            </div>
          </div>

          {/* ── Row 2: Zone Axis + g-Vector ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="modal-input-group">
              <label>Zone Axis</label>
              <input
                type="text"
                value={zoneAxis}
                onChange={(e) => setZoneAxis(e.target.value)}
                placeholder="e.g. 011"
              />
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                Viewing direction, e.g. 011, 001, 111
              </div>
            </div>
            <div className="modal-input-group">
              <label>Diffraction Vector g</label>
              <input
                type="text"
                value={gVector}
                onChange={(e) => setGVector(e.target.value)}
                placeholder="e.g. [2,0,0]"
              />
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                Active g-vector used for imaging, e.g. [2,0,0]
              </div>
            </div>
          </div>

          {/* ── Instrument Rotation φ ── the key scientific input ── */}
          <div className="phi-box">
            <div className="phi-box__title">
              📐 Instrument Rotation Angle φ
              <span className="phi-badge">
                {rotationDeg >= 0 ? '+' : ''}{rotationDeg}°
              </span>
            </div>
            <div className="phi-box__desc">
              The rotational offset between your microscope's diffraction plane and image plane.
              This is unique to each instrument and determines how the morphological reference map 
              is aligned with your TEM image.
            </div>

            {/* Microscope Preset Selector */}
            <div className="modal-input-group" style={{ marginTop: '0.75rem' }}>
              <label>Select your instrument (auto-fills φ)</label>
              <select
                value={microscopePreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                style={{ fontFamily: 'monospace' }}
              >
                {MICROSCOPE_PRESETS.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.label}{p.phi !== null ? `  —  φ = ${p.phi}°` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Manual φ input */}
            <div className="modal-input-group" style={{ marginTop: '0.75rem' }}>
              <label>Or enter φ manually (degrees)</label>
              <input
                type="number"
                value={rotationDeg}
                onChange={(e) => { setRotationDeg(e.target.value); setMicroscopePreset('custom'); }}
                min="-180" max="360" step="1"
                placeholder="e.g. 32"
                style={{ fontFamily: 'monospace', letterSpacing: '0.05em' }}
              />
              <div style={{ fontSize: '0.72rem', color: '#fbbf24', marginTop: '4px' }}>
                ⚠ Verify this value from your microscope session log or a known MoO₃ calibration standard before publishing results.
              </div>
            </div>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '0' }} />

          {/* ── Detection Sensitivity ── */}
          <div className="modal-input-group">
            <label>Detection Sensitivity: <strong style={{ color: 'var(--accent-color)' }}>{sensitivity}</strong></label>
            <input
              type="range"
              min="0.01" max="0.5" step="0.01"
              value={sensitivity}
              onChange={(e) => setSensitivity(parseFloat(e.target.value))}
            />
            <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', display: 'flex', justifyContent: 'space-between' }}>
              <span>← More sensitive (fainter loops)</span>
              <span>Less sensitive (obvious loops only) →</span>
            </div>
          </div>

          {/* ── FFT Toggle ── */}
          <div className="modal-input-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.75rem' }}>
            <input
              type="checkbox"
              id="modalFftToggle"
              checked={enableFFT}
              onChange={(e) => setEnableFFT(e.target.checked)}
              style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer' }}
            />
            <div>
              <label htmlFor="modalFftToggle" style={{ cursor: 'pointer', margin: 0 }}>
                Enable FFT Lattice Suppression
              </label>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                Only for high-res images showing a clear atomic lattice background.
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="modal-btn cancel" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="modal-btn primary">
              Confirm &amp; Analyze →
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
