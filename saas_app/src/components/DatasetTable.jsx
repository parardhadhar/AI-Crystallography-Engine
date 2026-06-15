import { useState, useEffect, useMemo } from 'react'
import './DatasetTable.css'

export default function DatasetTable() {
  const [allData, setAllData] = useState(null)   // null = loading, [] = error/empty
  const [error, setError] = useState(null)

  const [material, setMaterial] = useState('FCC')
  const [zoneAxis, setZoneAxis] = useState(null)
  const [gVector, setGVector] = useState(null)
  const [morphFilter, setMorphFilter] = useState('All')
  const [visFilter, setVisFilter] = useState('All')

  // ── 1. Fetch once on mount ─────────────────────────────────────────────────
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/dataset')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(json => {
        if (json.status !== 'success') throw new Error(json.message || 'API error')
        setAllData(json.data)
      })
      .catch(err => {
        console.error(err)
        setError(err.message)
        setAllData([])
      })
  }, [])

  // ── 2. Cascade: derive available zone axes for selected material ───────────
  const zoneAxes = useMemo(() => {
    if (!allData) return []
    const s = new Set(allData.filter(r => r.Material === material).map(r => r.Zone_Axis_B))
    return Array.from(s).sort()
  }, [allData, material])

  // Auto-select first zone axis when list changes
  useEffect(() => {
    if (zoneAxes.length === 0) return
    setZoneAxis(za => (za && zoneAxes.includes(za) ? za : zoneAxes[0]))
  }, [zoneAxes])

  // ── 3. Cascade: derive available g-vectors for selected zone axis ──────────
  const gVectors = useMemo(() => {
    if (!allData || !zoneAxis) return []
    const s = new Set(
      allData
        .filter(r => r.Material === material && r.Zone_Axis_B === zoneAxis)
        .map(r => r.Diffraction_Vector_g)
    )
    return Array.from(s).sort()
  }, [allData, material, zoneAxis])

  // Auto-select first g-vector when list changes
  useEffect(() => {
    if (gVectors.length === 0) return
    setGVector(gv => (gv && gVectors.includes(gv) ? gv : gVectors[0]))
  }, [gVectors])

  // ── 4. Final filtered results ──────────────────────────────────────────────
  const results = useMemo(() => {
    if (!allData || !zoneAxis || !gVector) return []
    return allData.filter(r => {
      if (r.Material !== material || r.Zone_Axis_B !== zoneAxis || r.Diffraction_Vector_g !== gVector) return false;
      if (morphFilter !== 'All') {
        const isEdge = r.Morphology?.toLowerCase().includes('edge');
        if (morphFilter === 'Edge-On' && !isEdge) return false;
        if (morphFilter === 'Inclined' && isEdge) return false;
      }
      if (visFilter !== 'All') {
        if (visFilter === 'Visible' && r.Visibility_gb !== 'Visible') return false;
        if (visFilter === 'Invisible' && r.Visibility_gb !== 'Invisible') return false;
      }
      return true;
    })
  }, [allData, material, zoneAxis, gVector, morphFilter, visFilter])

  // ── Helpers ───────────────────────────────────────────────────────────────
  const isLoading = allData === null
  const isReady   = !isLoading && !error && zoneAxis && gVector

  return (
    <div className="dt-root">
      {/* ── Header ── */}
      <div className="dt-head">
        <div>
          <h2 className="dt-title">Morphology Lookup Table</h2>
          <p className="dt-subtitle">
            Select a material, zone axis, and diffraction vector to retrieve all predicted loop states.
          </p>
        </div>
        {isReady && (
          <div className="dt-badge">{results.length} variants</div>
        )}
      </div>

      {/* ── Dropdowns ── */}
      <div className="dt-filters">
        {/* Step 1 */}
        <div className="dt-filter-item">
          <label className="dt-label">Material System</label>
          <select
            className="dt-select"
            value={material}
            onChange={e => { setMaterial(e.target.value); setZoneAxis(null); setGVector(null) }}
          >
            <option value="FCC">FCC — Face-Centered Cubic</option>
            <option value="BCC">BCC — Body-Centered Cubic</option>
          </select>
        </div>

        {/* Step 2 */}
        <div className="dt-filter-item">
          <label className="dt-label">Zone Axis (B)</label>
          {isLoading ? (
            <div className="dt-skeleton" />
          ) : (
            <select
              className="dt-select dt-select--mono"
              value={zoneAxis || ''}
              onChange={e => { setZoneAxis(e.target.value); setGVector(null) }}
              disabled={zoneAxes.length === 0}
            >
              {zoneAxes.map(za => (
                <option key={za} value={za}>{za}</option>
              ))}
            </select>
          )}
        </div>

        {/* Step 3 */}
        <div className="dt-filter-item">
          <label className="dt-label">Diffraction Vector (g)</label>
          {isLoading ? (
            <div className="dt-skeleton" />
          ) : (
            <select
              className="dt-select dt-select--mono"
              value={gVector || ''}
              onChange={e => setGVector(e.target.value)}
              disabled={gVectors.length === 0}
            >
              {gVectors.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          )}
        </div>

        {/* Step 4: Adv. Filters */}
        <div className="dt-filter-item">
          <label className="dt-label">Morphology</label>
          <select className="dt-select" value={morphFilter} onChange={e => setMorphFilter(e.target.value)}>
            <option value="All">All Morphologies</option>
            <option value="Edge-On">Edge-On Only</option>
            <option value="Inclined">Inclined Only</option>
          </select>
        </div>

        <div className="dt-filter-item">
          <label className="dt-label">Visibility</label>
          <select className="dt-select" value={visFilter} onChange={e => setVisFilter(e.target.value)}>
            <option value="All">All Visibilities</option>
            <option value="Visible">Visible Only</option>
            <option value="Invisible">Invisible Only</option>
          </select>
        </div>
      </div>

      {/* ── State messages ── */}
      {isLoading && <div className="dt-state">Loading physics data…</div>}
      {error    && <div className="dt-state dt-state--error">Error: {error}</div>}

      {/* ── Results table ── */}
      {isReady && (
        <div className="dt-table-wrap">
          <table className="dt-table">
            <thead>
              <tr>
                <th>Variant</th>
                <th>Family</th>
                <th>Morphology</th>
                <th>Visibility (g·b)</th>
                <th>Classification</th>
                <th>Colour</th>
              </tr>
            </thead>
            <tbody>
              {results.map((row, i) => {
                const edgeOn = row.Morphology?.toLowerCase().includes('edge')
                const visible = row.Visibility_gb === 'Visible'
                return (
                  <tr key={i}>
                    <td className="td-mono">{row.Variant_Name}</td>
                    <td>{row.Loop_Family}</td>
                    <td>
                      <span className={`pill ${edgeOn ? 'pill--edge' : 'pill--inclined'}`}>
                        {row.Morphology}
                      </span>
                    </td>
                    <td>
                      <span className={`pill ${visible ? 'pill--visible' : 'pill--invisible'}`}>
                        {visible ? 'Visible' : 'Invisible (g·b=0)'}
                      </span>
                    </td>
                    <td className="td-small">{row.AI_UI_Classification}</td>
                    <td>
                      <div className="td-color">
                        <span className="color-dot" style={{ background: row.UI_Color_Hex }} />
                        <span className="td-mono">{row.UI_Color_Hex}</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {results.length === 0 && (
                <tr>
                  <td colSpan={6} className="td-empty">No variants found for this condition.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── FAQ ── */}
      <div className="dt-faq">
        <div className="dt-faq-item">
          <div className="dt-faq-q">Why is a loop invisible?</div>
          <div className="dt-faq-a">
            When the dot product of the diffraction vector <strong>g</strong> and the Burgers vector <strong>b</strong> equals zero (g·b = 0), the strain field of the loop produces no diffraction contrast. The loop is present but cannot be seen.
          </div>
        </div>
        <div className="dt-faq-item">
          <div className="dt-faq-q">Edge-On vs. Inclined?</div>
          <div className="dt-faq-a">
            When the beam direction <strong>B</strong> lies in the loop plane (B·n = 0), the loop appears as a thin straight line (edge-on). Otherwise, the projected shape is an ellipse whose aspect ratio depends on the tilt angle.
          </div>
        </div>
        <div className="dt-faq-item">
          <div className="dt-faq-q">FCC vs. BCC loops?</div>
          <div className="dt-faq-a">
            FCC uses <strong>1/3⟨111⟩</strong> faulted and <strong>⟨110⟩</strong> perfect loop families. BCC uses <strong>1/2⟨111⟩</strong> and <strong>⟨100⟩</strong> loop families with distinct contrast rules.
          </div>
        </div>
      </div>
    </div>
  )
}
