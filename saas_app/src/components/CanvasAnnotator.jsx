import React, { useRef, useState, useEffect } from 'react';
import './CanvasAnnotator.css';

export default function CanvasAnnotator({ imageUrl, scale, watermarkText, showWatermark, agentCommand, rawFile, onSnapshotGenerated }) {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  
  // Studio Tools
  const [tool, setTool] = useState('pan'); // 'pan', 'pen', 'circle', 'measure', 'eraser'
  
  // Image Adjustments
  const [filters, setFilters] = useState({
    brightness: 100,
    contrast: 100,
    invert: false,
    exposure: 100
  });
  
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  
  // Drawing State
  const [isDrawing, setIsDrawing] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const [startPos, setStartPos] = useState(null);
  const [lastPos, setLastPos] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [currentMeasure, setCurrentMeasure] = useState(null);
  const [currentCircle, setCurrentCircle] = useState(null);

  // Server Fetches
  const [fftImageUrl, setFftImageUrl] = useState(null);
  const [isFftLoading, setFftLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const scalePx = parseFloat(scale) || 120;
  const nmPerPixel = 100 / scalePx;

  // Snapshot functionality for the Report Builder
  const triggerSnapshot = () => {
    if (!onSnapshotGenerated || !canvasRef.current || !imageRef.current) return;
    try {
      const exportCanvas = document.createElement('canvas');
      exportCanvas.width = dimensions.width || imageRef.current.width;
      exportCanvas.height = dimensions.height || imageRef.current.height;
      if (exportCanvas.width === 0) return;
      const ctx = exportCanvas.getContext('2d');
      ctx.drawImage(imageRef.current, 0, 0, exportCanvas.width, exportCanvas.height);
      ctx.drawImage(canvasRef.current, 0, 0);
      onSnapshotGenerated(exportCanvas.toDataURL('image/png'));
    } catch (e) {
      console.warn('Snapshot failed:', e);
    }
  };

  // Trigger snapshot when dimensions change or after image loads
  useEffect(() => {
    const timer = setTimeout(triggerSnapshot, 500);
    return () => clearTimeout(timer);
  }, [dimensions, imageUrl]);

  // Agentic AI Listener
  useEffect(() => {
    if (agentCommand && agentCommand.action) {
      const action = agentCommand.action;
      if (action === 'TOOL_PAN') setTool('pan');
      else if (action === 'TOOL_PEN') setTool('pen');
      else if (action === 'TOOL_CIRCLE') setTool('circle');
      else if (action === 'TOOL_MEASURE') setTool('measure');
      else if (action === 'TOOL_ERASER') setTool('eraser');
      else if (action === 'TOGGLE_DARK_FIELD') {
        setFilters(prev => ({ ...prev, invert: !prev.invert }));
      }
      else if (action === 'CLEAR_CANVAS') {
        if (canvasRef.current && dimensions.width > 0) {
           const ctx = canvasRef.current.getContext('2d');
           ctx.clearRect(0, 0, dimensions.width, dimensions.height);
           triggerSnapshot();
        }
      }
      else if (action === 'FOURIER_FILTER') handleFourierFilter();
      else if (action === 'EXPORT_TIFF') exportStudio();
    }
  }, [agentCommand, dimensions]);

  useEffect(() => {
    const updateDimensions = () => {
      if (imageRef.current) {
        setDimensions({
          width: imageRef.current.width,
          height: imageRef.current.height
        });
      }
    };
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const handleImageLoad = () => {
    if (imageRef.current) {
      setDimensions({
        width: imageRef.current.width,
        height: imageRef.current.height
      });
    }
  };

  const getCoordinates = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return {x: 0, y: 0};
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    return {x, y};
  };

  const handleMouseDown = (e) => {
    if (e.button === 1 || tool === 'pan') {
      e.preventDefault();
      setIsPanning(true);
      setLastPos({ x: e.clientX, y: e.clientY });
      return;
    }

    const {x, y} = getCoordinates(e);
    setIsDrawing(true);
    setStartPos({ x, y });
    setLastPos({ x, y });
  };

  const handleMouseMove = (e) => {
    if (isPanning && lastPos) {
      const dx = e.clientX - lastPos.x;
      const dy = e.clientY - lastPos.y;
      setPanOffset(prev => ({ x: prev.x + dx / zoom, y: prev.y + dy / zoom }));
      setLastPos({ x: e.clientX, y: e.clientY });
      return;
    }

    if (!isDrawing) return;
    const {x, y} = getCoordinates(e);
    const ctx = canvasRef.current.getContext('2d');

    if (tool === 'pen' && lastPos) {
      ctx.globalCompositeOperation = 'source-over';
      ctx.beginPath();
      ctx.moveTo(lastPos.x, lastPos.y);
      ctx.lineTo(x, y);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#00e5ff';
      ctx.stroke();
      setLastPos({x, y});
    } else if (tool === 'eraser' && lastPos) {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.beginPath();
      ctx.moveTo(lastPos.x, lastPos.y);
      ctx.lineTo(x, y);
      ctx.lineWidth = 20;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowBlur = 0;
      ctx.stroke();
      setLastPos({x, y});
    } else if (tool === 'measure' && startPos) {
      const distPx = Math.sqrt(Math.pow(x - startPos.x, 2) + Math.pow(y - startPos.y, 2));
      const distNm = distPx * nmPerPixel;
      setCurrentMeasure({ x, y, value: distNm.toFixed(2) + ' nm' });
    } else if (tool === 'circle' && startPos) {
      const radius = Math.sqrt(Math.pow(x - startPos.x, 2) + Math.pow(y - startPos.y, 2));
      setCurrentCircle({ x: startPos.x, y: startPos.y, r: radius });
    }
  };

  const handleMouseUp = (e) => {
    if (isPanning) {
      setIsPanning(false);
      setLastPos(null);
      return;
    }

    if (!isDrawing) return;
    setIsDrawing(false);
    
    const {x, y} = getCoordinates(e);
    const ctx = canvasRef.current.getContext('2d');

    if (tool === 'circle' && startPos) {
      const radius = Math.sqrt(Math.pow(x - startPos.x, 2) + Math.pow(y - startPos.y, 2));
      ctx.globalCompositeOperation = 'source-over';
      ctx.beginPath();
      ctx.arc(startPos.x, startPos.y, radius, 0, 2 * Math.PI);
      ctx.strokeStyle = '#ff007f';
      ctx.lineWidth = 3;
      ctx.shadowBlur = 15;
      ctx.shadowColor = '#ff007f';
      ctx.stroke();
      setCurrentCircle(null);
    } else if (tool === 'measure' && startPos) {
      ctx.globalCompositeOperation = 'source-over';
      ctx.beginPath();
      ctx.moveTo(startPos.x, startPos.y);
      ctx.lineTo(x, y);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.stroke();
      ctx.setLineDash([]);
      
      const distPx = Math.sqrt(Math.pow(x - startPos.x, 2) + Math.pow(y - startPos.y, 2));
      const distNm = distPx * nmPerPixel;
      
      ctx.font = 'bold 16px Inter';
      ctx.fillStyle = '#00e5ff';
      ctx.shadowBlur = 5;
      ctx.shadowColor = '#000';
      ctx.fillText(distNm.toFixed(2) + ' nm', x + 10, y + 10);
      
      setCurrentMeasure(null);
    }
    
    setStartPos(null);
    setLastPos(null);
    triggerSnapshot();
  };

  const clearCanvas = () => {
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);
  };

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const exportStudio = () => {
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = dimensions.width;
    exportCanvas.height = dimensions.height;
    const ctx = exportCanvas.getContext('2d');
    
    ctx.filter = `brightness(${filters.brightness}%) contrast(${filters.contrast}%) saturate(${filters.exposure}%) ${filters.invert ? 'invert(100%)' : ''}`;
    ctx.drawImage(imageRef.current, 0, 0, dimensions.width, dimensions.height);
    
    ctx.filter = 'none';
    ctx.drawImage(canvasRef.current, 0, 0);

    if (showWatermark && watermarkText) {
      ctx.font = '500 24px Inter, sans-serif';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
      ctx.shadowBlur = 8;
      ctx.textAlign = 'right';
      ctx.fillText(watermarkText, dimensions.width - 20, dimensions.height - 20);
    }
    
    const link = document.createElement('a');
    link.download = 'TEM_Studio_Analysis.png';
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
  };

  const handleFourierFilter = async () => {
    if (!rawFile) return;
    setFftLoading(true);
    const formData = new FormData();
    formData.append('file', rawFile);
    try {
      const res = await fetch('http://127.0.0.1:8000/fft_spectrum', { method: 'POST', body: formData });
      const json = await res.json();
      if (json.status === 'success') {
        setFftImageUrl(json.fft_data_url);
      }
    } catch (e) { 
      console.error(e); 
      alert("Failed to compute True Fourier Transform.");
    }
    setFftLoading(false);
  };

  const submitCorrections = async () => {
    if (!canvasRef.current) return;
    setIsSubmitting(true);
    const maskData = canvasRef.current.toDataURL('image/png');
    
    try {
      const res = await fetch('http://127.0.0.1:8000/learn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mask_b64: maskData })
      });
      const json = await res.json();
      if (json.status === 'success') {
        alert("Training data submitted! The neural engine will learn from your manual corrections.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to submit corrections.");
    }
    setIsSubmitting(false);
  };

  return (
    <div className="studio-wrapper animate-in delay-2">
      {/* Left Toolbar */}
      <div className="studio-sidebar">
        <div className="sidebar-section">
          <span className="section-title">Canvas Tools</span>
          <div className="tool-list" style={{ marginBottom: '1.5rem' }}>
            <button className={`studio-btn ${tool === 'pan' ? 'active' : ''}`} onClick={() => setTool('pan')}>Infinite Pan</button>
            <button className="studio-btn" onClick={handleFourierFilter} disabled={isFftLoading}>
              {isFftLoading ? 'Calculating FFT...' : 'Reciprocal Lattice (FFT)'}
            </button>
          </div>

          <span className="section-title">Annotation Tools</span>
          <div className="tool-list">
            <button className={`studio-btn ${tool === 'pen' ? 'active' : ''}`} onClick={() => setTool('pen')}>Neon Marker</button>
            <button className={`studio-btn ${tool === 'circle' ? 'active' : ''}`} onClick={() => setTool('circle')}>Geometry Circle</button>
            <button className={`studio-btn ${tool === 'measure' ? 'active' : ''}`} onClick={() => setTool('measure')}>Measurement Scale</button>
            <button className={`studio-btn ${tool === 'eraser' ? 'active' : ''}`} onClick={() => setTool('eraser')}>Precision Eraser</button>
          </div>
        </div>
        
        <div className="sidebar-section" style={{ marginTop: 'auto' }}>
          <button className="studio-btn" style={{ marginBottom: '0.5rem', background: 'rgba(0, 229, 255, 0.1)', color: '#00e5ff', borderColor: 'rgba(0, 229, 255, 0.3)' }} onClick={submitCorrections} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Submit to AI Training'}
          </button>
          <button className="studio-btn danger" onClick={clearCanvas}>Clear Annotations</button>
        </div>
      </div>

      {/* Central Stage */}
      <div className="studio-stage" style={{ overflow: 'hidden' }}>
        <div 
          className="stage-inner" 
          style={{ 
            transform: `scale(${zoom}) translate(${panOffset.x}px, ${panOffset.y}px)`,
            cursor: tool === 'pan' ? (isPanning ? 'grabbing' : 'grab') : 'crosshair'
          }}
        >
          <img 
            ref={imageRef} 
            src={imageUrl} 
            alt="TEM Studio" 
            className="studio-image" 
            onLoad={handleImageLoad}
            style={{
              filter: `brightness(${filters.brightness}%) contrast(${filters.contrast}%) saturate(${filters.exposure}%) ${filters.invert ? 'invert(100%)' : ''}`
            }}
          />
          <canvas
            ref={canvasRef}
            width={dimensions.width}
            height={dimensions.height}
            className="studio-canvas"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          />
          {currentCircle && (
            <div 
              style={{
                position: 'absolute',
                left: currentCircle.x - currentCircle.r,
                top: currentCircle.y - currentCircle.r,
                width: currentCircle.r * 2,
                height: currentCircle.r * 2,
                borderRadius: '50%',
                border: '3px solid #ff007f',
                boxShadow: '0 0 15px #ff007f',
                pointerEvents: 'none'
              }}
            />
          )}
          {currentMeasure && (
            <div className="measure-tooltip" style={{ left: currentMeasure.x, top: currentMeasure.y }}>
              {currentMeasure.value}
            </div>
          )}
        </div>
        
        {/* FFT Overlay Modal */}
        {fftImageUrl && (
          <div style={{
            position: 'absolute', top: 20, right: 20, 
            width: '300px', height: '300px', 
            background: 'rgba(10,10,15,0.85)', backdropFilter: 'blur(10px)',
            borderRadius: '12px', border: '1px solid rgba(0, 229, 255, 0.3)',
            boxShadow: '0 10px 40px rgba(0,0,0,0.8)',
            display: 'flex', flexDirection: 'column', overflow: 'hidden', zIndex: 100
          }}>
            <div style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#00e5ff' }}>True FFT Magnitude</span>
              <button onClick={() => setFftImageUrl(null)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>✕</button>
            </div>
            <img src={fftImageUrl} alt="FFT Spectrum" style={{ flex: 1, objectFit: 'contain', width: '100%' }} />
          </div>
        )}
      </div>

      {/* Right Filters */}
      <div className="studio-sidebar right">
        <div className="sidebar-section">
          <span className="section-title">Micrograph Tuning</span>
          
          <div className="slider-group">
            <div className="slider-header">
              <span>Brightness</span>
              <span>{filters.brightness}%</span>
            </div>
            <input type="range" min="0" max="200" value={filters.brightness} className="studio-slider" onChange={(e) => updateFilter('brightness', e.target.value)} />
          </div>

          <div className="slider-group">
            <div className="slider-header">
              <span>Contrast</span>
              <span>{filters.contrast}%</span>
            </div>
            <input type="range" min="0" max="200" value={filters.contrast} className="studio-slider" onChange={(e) => updateFilter('contrast', e.target.value)} />
          </div>

          <div className="slider-group">
            <div className="slider-header">
              <span>Exposure Depth</span>
              <span>{filters.exposure}%</span>
            </div>
            <input type="range" min="0" max="200" value={filters.exposure} className="studio-slider" onChange={(e) => updateFilter('exposure', e.target.value)} />
          </div>
          
          <button 
            className={`studio-btn ${filters.invert ? 'active' : ''}`} 
            style={{ marginTop: '1rem' }}
            onClick={() => updateFilter('invert', !filters.invert)}
          >
            Toggle Dark Field
          </button>
        </div>

        <div className="sidebar-section">
          <span className="section-title">Optical Zoom</span>
          <div className="slider-group">
            <div className="slider-header">
              <span>Magnification</span>
              <span>{Math.round(zoom * 100)}%</span>
            </div>
            <input type="range" min="0.5" max="3" step="0.1" value={zoom} className="studio-slider" onChange={(e) => setZoom(parseFloat(e.target.value))} />
          </div>
        </div>

        <button className="studio-btn primary" onClick={exportStudio}>Export High-Res PNG</button>
      </div>
    </div>
  );
}
