import React, { useRef, useState } from 'react';
import html2pdf from 'html2pdf.js';
import MorphologyMapOverlay from './MorphologyMapOverlay';
import './ReportEditor.css';

export default function ReportEditor({ 
  originalImage,
  analyzedImage, 
  defects, 
  scientistName, 
  material, 
  zoneAxis, 
  gVector, 
  scale,
  rotationDeg
}) {
  const reportRef = useRef(null);
  const [logo, setLogo] = useState(null);
  const [summary, setSummary] = useState('');

  const handleLogoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => setLogo(event.target.result);
      reader.readAsDataURL(file);
    }
  };

  const exportPDF = () => {
    if (!reportRef.current) return;
    
    const opt = {
      margin:       [10, 0, 10, 0],
      filename:     `TEM_Analysis_${new Date().toISOString().split('T')[0]}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
    };
    
    html2pdf().set(opt).from(reportRef.current).save().catch(err => {
      console.error('PDF Export Error:', err);
      alert('Failed to export PDF.');
    });
  };

  const exportCSV = () => {
    if (!defects || defects.length === 0) {
      alert("No defect data to export.");
      return;
    }
    const headers = ["Type Classification", "Diameter (nm)", "Area (nm2)", "Angle (deg)"];
    const rows = defects.map(d => [d.type, d.diameter_nm, d.area_nm2, d.angle_deg]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(",") + "\n" 
      + rows.map(e => e.join(",")).join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `TEM_Defects_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const perfectCount = defects?.filter(d => d.type.includes('Perfect')).length || 0;
  const faultedCount = defects?.filter(d => d.type.includes('Faulted')).length || 0;
  const edgeOnCount = defects?.filter(d => d.type.includes('Edge-On')).length || 0;
  const unknownCount = defects?.filter(d => d.type === 'Unknown' || d.type.includes('Ambiguous')).length || 0;
  const totalArea = defects?.reduce((sum, d) => sum + (d.area_nm2 || 0), 0) || 0;

  return (
    <div className="report-builder-container">
      <div className="report-toolbar">
        <div className="toolbar-group">
          <label className="toolbar-btn file-upload-btn" title="Upload custom logo">
            <input type="file" accept="image/*" onChange={handleLogoUpload} style={{ display: 'none' }} />
            🏢 Set Organization Logo
          </label>
        </div>
        <div className="toolbar-group export-group">
          <button className="toolbar-btn" onClick={exportCSV} style={{ marginRight: '10px' }}>
            📊 Export Raw Data (CSV)
          </button>
          <button className="export-pdf-btn" onClick={exportPDF}>
            📥 Download Professional PDF
          </button>
        </div>
      </div>

      <div className="report-editor-wrapper">
        <div className="a4-report-page" ref={reportRef}>
          
          {/* Header Section */}
          <header className="report-header">
            <div className="header-brand">
              <div 
                className="logo-placeholder" 
                onClick={() => document.querySelector('.file-upload-btn input').click()}
              >
                {logo ? <img src={logo} alt="Organization Logo" /> : <span>Click to add Logo</span>}
              </div>
            </div>
            <div className="header-title">
              <h1 contentEditable suppressContentEditableWarning>Transmission Electron Microscopy Analysis</h1>
              <p className="subtitle" contentEditable suppressContentEditableWarning>Automated Crystallographic Defect Characterisation</p>
            </div>
          </header>

          <hr className="report-divider" />

          {/* Metadata Grid */}
          <section className="metadata-section">
            <div className="metadata-grid">
              <div className="meta-item">
                <span className="meta-label">Investigator</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>{scientistName || 'N/A'}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Date of Analysis</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>{new Date().toLocaleDateString()}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Crystal System</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>{material || 'Unknown'}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Zone Axis (B)</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>[{zoneAxis || '---'}]</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Diffraction Vector (g)</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>{gVector || '---'}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Scale Calibration</span>
                <span className="meta-value" contentEditable suppressContentEditableWarning>{scale || '0'} px/100nm</span>
              </div>
            </div>
          </section>

          {/* Executive Summary */}
          <section className="summary-section">
            <h2 contentEditable suppressContentEditableWarning>Executive Summary</h2>
            <textarea 
              className="summary-textarea"
              placeholder="Click here to type your conclusions, hypotheses, or contextual notes regarding the sample..."
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </section>

          {/* Page Break for PDF Export */}
          <div className="html2pdf__page-break"></div>

          {/* Side-by-Side Visual Comparison & Morphology Map */}
          <section className="visual-section" style={{ marginTop: '2rem' }}>
            <h2 contentEditable suppressContentEditableWarning>Microstructural Evidence & Morphological Analysis</h2>
            
            <div className="visual-comparison-grid">
              <div className="image-panel">
                <h3 contentEditable suppressContentEditableWarning>Original Micrograph</h3>
                <div className="image-container">
                  {originalImage ? (
                    <img src={originalImage} alt="Original Micrograph" className="analyzed-img" />
                  ) : (
                    <div className="image-placeholder">No original image available.</div>
                  )}
                </div>
              </div>

              <div className="image-panel">
                <h3 contentEditable suppressContentEditableWarning>AI-Detected Defects</h3>
                <div className="image-container">
                  {analyzedImage ? (
                    <img src={analyzedImage} alt="Analyzed Micrograph" className="analyzed-img" />
                  ) : (
                    <div className="image-placeholder">No analyzed image available.</div>
                  )}
                </div>
              </div>
            </div>

            <div className="morphology-map-container" style={{ marginTop: '2rem' }}>
              <h3 contentEditable suppressContentEditableWarning style={{ textAlign: 'center', marginBottom: '1rem', color: '#1e293b' }}>
                Crystallographic Reference Map
              </h3>
              <div className="map-embed-wrapper" style={{ display: 'flex', justifyContent: 'center' }}>
                <MorphologyMapOverlay 
                  rotationDeg={rotationDeg} 
                  gVector={gVector} 
                  zoneAxis={zoneAxis} 
                  defects={defects} 
                  isStatic={true} 
                />
              </div>
            </div>
          </section>

          {/* Statistical Breakdown */}
          <section className="stats-section">
            <h2 contentEditable suppressContentEditableWarning>Statistical Summary</h2>
            <div className="stats-cards">
              <div className="stat-card">
                <span className="stat-number" contentEditable suppressContentEditableWarning>{defects ? defects.length : 0}</span>
                <span className="stat-label">Total Features</span>
              </div>
              <div className="stat-card" style={{borderColor: '#ff69b4'}}>
                <span className="stat-number" contentEditable suppressContentEditableWarning>{perfectCount}</span>
                <span className="stat-label">Perfect Loops</span>
              </div>
              <div className="stat-card" style={{borderColor: '#00ffff'}}>
                <span className="stat-number" contentEditable suppressContentEditableWarning>{faultedCount}</span>
                <span className="stat-label">Faulted Loops</span>
              </div>
              <div className="stat-card" style={{borderColor: '#ffff00'}}>
                <span className="stat-number" contentEditable suppressContentEditableWarning>{edgeOnCount}</span>
                <span className="stat-label">Edge-On</span>
              </div>
              <div className="stat-card" style={{borderColor: '#777'}}>
                <span className="stat-number" contentEditable suppressContentEditableWarning>{unknownCount}</span>
                <span className="stat-label">Ambiguous</span>
              </div>
            </div>
            <p className="table-footer" style={{ textAlign: 'center', marginTop: '1.5rem' }} contentEditable suppressContentEditableWarning>
              Total extracted defective area: {Math.round(totalArea)} nm²
            </p>
          </section>

        </div>
      </div>
    </div>
  );
}
