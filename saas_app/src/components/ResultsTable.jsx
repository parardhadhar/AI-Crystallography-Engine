import React from 'react'

export default function ResultsTable({ data }) {
  if (!data) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {Object.entries(data).map(([key, value], idx) => {
        const delayClass = `delay-${(idx % 4) + 1}`;
        // Format the key (e.g. defect_type -> Defect Type)
        const formattedKey = key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

        return (
          <div 
            key={key} 
            className={`animate-in ${delayClass}`}
            style={{
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-light)',
              borderRadius: '8px',
              padding: '1rem 1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              transition: 'all 0.3s var(--ease-smooth)'
            }}
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {formattedKey}
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              {value}
            </div>
          </div>
        )
      })}
    </div>
  )
}

