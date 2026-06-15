import React, { useState, useEffect } from 'react';

export default function ProgressBar() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Simulate deterministic progress while waiting for the heavy Python AI backend
    const interval = setInterval(() => {
      setProgress(old => {
        // Asymptotically approach 95% (the last 5% happens when the API resolves)
        const diff = 95 - old;
        if (old >= 95) return 95;
        // Move faster initially, then slow down
        return old + (diff * 0.05); 
      });
    }, 200);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'rgba(0,0,0,0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 50,
      color: '#fff',
      gap: '1.5rem',
      borderRadius: '12px'
    }}>
      <div style={{ 
        fontSize: '1.125rem', 
        fontWeight: 500, 
        letterSpacing: '0.05em',
        color: '#00e5ff',
        textShadow: '0 0 10px rgba(0, 229, 255, 0.5)'
      }}>
        Neural Engine Processing...
      </div>
      
      <div style={{
        width: '60%',
        maxWidth: '300px',
        height: '4px',
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '2px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${progress}%`,
          height: '100%',
          background: '#00e5ff',
          transition: 'width 0.2s ease-out',
          boxShadow: '0 0 15px #00e5ff'
        }} />
      </div>
      
      <div style={{ 
        fontSize: '0.85rem', 
        color: 'var(--text-tertiary)',
        minHeight: '1.2rem'
      }}>
        {progress < 15 ? 'Allocating GPU memory...' :
         progress < 30 ? 'Initializing Vision Transformer...' :
         progress < 50 ? 'Applying FFT Lattice Suppression...' :
         progress < 75 ? 'Segmenting physical loops...' :
         progress < 90 ? 'Solving Burgers Vectors (g.b=0)...' :
         'Generating visual composite overlays...'}
      </div>
    </div>
  );
}
