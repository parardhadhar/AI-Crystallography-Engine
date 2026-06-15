import React, { useState } from 'react';

const DiffusionEngine = ({ scientistName, gVector, zoneAxis }) => {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [defectType, setDefectType] = useState('Perfect 1/2<110>');
  const [noiseLevel, setNoiseLevel] = useState(0.5);
  const [batchSize, setBatchSize] = useState(500);

  const [images, setImages] = useState([]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerated(false);
    
    try {
      const formData = new FormData();
      formData.append('defect_type', defectType);
      formData.append('noise_level', noiseLevel.toString());
      formData.append('batch_size', batchSize.toString());

      const response = await fetch('http://127.0.0.1:8000/generate_synthetic', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const json = await response.json();
      
      if (json.status === 'success') {
        setImages(json.images);
        setGenerated(true);
      }
    } catch (err) {
      console.error('Synthesis Error:', err);
      alert('Neural Engine Error. Is the backend server running on port 8000?');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="diffusion-engine-container" style={{ padding: '2rem', display: 'flex', gap: '2rem', height: '100%', boxSizing: 'border-box' }}>
      
      {/* LEFT: Controls */}
      <div className="diffusion-controls" style={{
        flex: '0 0 320px', 
        background: 'rgba(255, 255, 255, 0.03)', 
        border: '1px solid rgba(255, 255, 255, 0.1)', 
        borderRadius: '12px', 
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem'
      }}>
        <div>
          <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', color: 'var(--text-primary)' }}>
            <span style={{ fontSize: '1.5rem', marginRight: '0.5rem' }}>🧬</span>
            Synthetic Engine
          </h2>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Augment your dataset by generating thousands of physics-accurate defect patches using our Latent Diffusion Model.
          </p>
        </div>

        <div className="control-group">
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Target Defect Family
          </label>
          <select 
            value={defectType} 
            onChange={e => setDefectType(e.target.value)}
            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', fontFamily: 'inherit' }}
          >
            <option value="Perfect 1/2<110>">Perfect Loop (1/2&lt;110&gt;)</option>
            <option value="Faulted 1/3<111>">Faulted Loop (1/3&lt;111&gt;)</option>
            <option value="BCC 1/2<111>">BCC Loop (1/2&lt;111&gt;)</option>
            <option value="BCC <100>">BCC Loop (&lt;100&gt;)</option>
          </select>
        </div>

        <div className="control-group">
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Background Noise Variance: {noiseLevel}
          </label>
          <input 
            type="range" 
            min="0.1" 
            max="1.0" 
            step="0.1" 
            value={noiseLevel}
            onChange={e => setNoiseLevel(e.target.value)}
            style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
          />
          <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '4px', textAlign: 'right' }}>
            Matches IISc TEM camera noise
          </div>
        </div>

        <div className="control-group">
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Batch Size
          </label>
          <input 
            type="number" 
            value={batchSize}
            onChange={e => setBatchSize(e.target.value)}
            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', fontFamily: 'inherit' }}
          />
        </div>

        <div style={{ marginTop: 'auto' }}>
          <button 
            onClick={handleGenerate}
            disabled={generating}
            style={{
              width: '100%',
              padding: '1rem',
              borderRadius: '8px',
              border: 'none',
              background: generating ? 'rgba(99, 102, 241, 0.5)' : 'var(--accent-primary)',
              color: 'white',
              fontWeight: 700,
              cursor: generating ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              boxShadow: generating ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.4)'
            }}
          >
            {generating ? '🧠 Synthesizing Data...' : '⚡ Generate Training Data'}
          </button>
        </div>
      </div>

      {/* RIGHT: Gallery */}
      <div className="diffusion-gallery" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: 0, color: 'var(--text-primary)', fontWeight: 600 }}>
            Generated Dataset
            {generated && <span style={{ marginLeft: '1rem', fontSize: '0.85rem', color: 'var(--success)', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 10px', borderRadius: '12px' }}>
              ✓ {batchSize} images generated
            </span>}
          </h3>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-tertiary)' }}>
            g: <strong>{gVector}</strong> | z: <strong>[{zoneAxis}]</strong>
          </div>
        </div>

        <div style={{
          flex: 1,
          background: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '12px',
          border: '1px dashed rgba(255, 255, 255, 0.1)',
          padding: '1.5rem',
          overflowY: 'auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: '1rem',
          alignContent: 'start'
        }}>
          {!generating && !generated ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', margin: 'auto', color: 'var(--text-tertiary)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>🌌</div>
              <p>Configure parameters and generate to eliminate domain shift.</p>
            </div>
          ) : generating ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', margin: 'auto', color: 'var(--accent-primary)' }}>
              <div className="spinner" style={{ fontSize: '2rem', marginBottom: '1rem' }}>↻</div>
              <p>Sampling from Latent Space...</p>
            </div>
          ) : (
            images.map((src, i) => (
              <div key={i} style={{
                aspectRatio: '1',
                background: '#111',
                borderRadius: '8px',
                overflow: 'hidden',
                position: 'relative',
                boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
                animation: `fadeIn 0.5s ease-out ${i * 0.05}s both`
              }}>
                <img src={src} alt="Synthetic Loop" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.7)', padding: '4px 8px', fontSize: '0.65rem', color: '#ccc', backdropFilter: 'blur(4px)' }}>
                  {defectType} | g{gVector}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .spinner {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default DiffusionEngine;
