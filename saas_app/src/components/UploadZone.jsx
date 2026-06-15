import React, { useRef, useState } from 'react'

export default function UploadZone({ onUpload, isAnalyzing }) {
  const fileInputRef = useRef(null)
  const [isHovered, setIsHovered] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setIsHovered(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0])
      e.target.value = ''
    }
  }

  return (
    <div 
      onDragOver={(e) => { e.preventDefault(); setIsHovered(true); }}
      onDragLeave={() => setIsHovered(false)}
      onDrop={handleDrop}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => !isAnalyzing && fileInputRef.current.click()}
      style={{
        position: 'relative',
        padding: '2rem 1.5rem',
        textAlign: 'center',
        background: 'var(--bg-panel)',
        border: `1px dashed ${isHovered ? 'var(--text-primary)' : 'var(--border-focus)'}`,
        borderRadius: '8px',
        cursor: isAnalyzing ? 'wait' : 'pointer',
        transition: 'all 0.3s var(--ease-smooth)',
        backgroundColor: isHovered ? 'var(--bg-hover)' : 'transparent',
      }}
    >
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleChange} 
        accept="image/tiff, image/jpeg, image/png"
        style={{ display: 'none' }} 
      />
      
      <div style={{
        transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
        transition: 'transform 0.3s var(--ease-smooth)'
      }}>
        <div style={{ 
          fontSize: '0.875rem', 
          fontWeight: 600, 
          color: 'var(--text-primary)',
          marginBottom: '0.25rem',
        }}>
          {isAnalyzing ? 'Extracting Physics Data...' : 'Upload TEM Micrograph'}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
          Drop .tif or .png files here
        </div>
      </div>
    </div>
  )
}

