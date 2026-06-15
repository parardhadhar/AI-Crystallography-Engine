import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import './AnalyticsPanel.css';

function buildHistogram(values, bins = 14) {
  if (!values || values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const step = (max - min) / bins || 1;
  const data = [];
  for (let i = 0; i < bins; i++) {
    const rangeStart = (min + i * step).toFixed(1);
    const count = values.filter(
      (v) => v >= min + i * step && v < min + (i + 1) * step
    ).length;
    data.push({ name: rangeStart, count });
  }
  return data;
}

const TYPE_COLORS = {
  '1/2<110> Perfect Loop': '#ff69b4',
  '1/2<111> Perfect Loop': '#ff69b4',
  '1/3<111> Faulted Loop': '#00ffff',
  'Edge-On':               '#ffff00',
  'Unknown':               '#888888',
};

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a2e',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '12px',
};

export default function AnalyticsPanel({ results, defects }) {
  if (!results) {
    return (
      <div className="analytics-empty">
        <div className="analytics-empty-icon">📊</div>
        <h3>No Analysis Data Yet</h3>
        <p>Upload and analyze a TEM micrograph from the left panel. Histograms and plots will appear here.</p>
      </div>
    );
  }

  const diameters = (defects || []).map((d) => d.diameter_nm);
  const areas = (defects || []).map((d) => d.area_nm2);

  const sizeData = buildHistogram(diameters);
  const areaData = buildHistogram(areas);

  // Pie chart data
  const typeCounts = {};
  (defects || []).forEach((d) => { typeCounts[d.type] = (typeCounts[d.type] || 0) + 1; });
  const pieData = Object.entries(typeCounts).map(([name, value]) => ({ name, value }));

  const exportCSV = () => {
    if (!defects || defects.length === 0) return;
    const header = 'Index,Type,Diameter (nm),Area (nm²),Orientation Angle (°)\n';
    const rows = defects.map((d, i) =>
      `${i + 1},${d.type},${d.diameter_nm},${d.area_nm2},${d.angle_deg ?? 'N/A'}`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'tem_defect_analysis.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="analytics-panel">

      {/* ── Metric Cards ── */}
      <div className="metric-cards">
        {Object.entries(results).map(([key, val]) => (
          <div className="metric-card" key={key}>
            <div className="metric-label">{key}</div>
            <div className="metric-value">{val}</div>
          </div>
        ))}
      </div>

      {/* ── Charts Row ── */}
      <div className="charts-grid">

        {/* Size Histogram */}
        <div className="chart-box">
          <div className="chart-title">📏 Size Distribution (nm)</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sizeData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `~${l} nm`}
                formatter={(v) => [v, 'Count']}
              />
              <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Area Histogram */}
        <div className="chart-box">
          <div className="chart-title">📐 Area Distribution (nm²)</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={areaData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `~${l} nm²`}
                formatter={(v) => [v, 'Count']}
              />
              <Bar dataKey="count" fill="#a855f7" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Defect Type Pie */}
        <div className="chart-box chart-box--pie">
          <div className="chart-title">🔵 Defect Type Breakdown</div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="45%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {pieData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={TYPE_COLORS[entry.name] || '#888888'}
                      stroke="rgba(0,0,0,0.3)"
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Legend
                  wrapperStyle={{ fontSize: '12px', color: '#94a3b8', paddingTop: '8px' }}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(v, name) => [v, name]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem', fontSize: '0.85rem' }}>
              No defect type data available
            </div>
          )}
        </div>

        {/* ── NEW: Loop Orientation Distribution Rose Chart ── */}
        <div className="chart-box chart-box--pie">
          <div className="chart-title">🧭 Loop Orientation Distribution</div>
          <OrientationRosePanel defects={defects || []} />
        </div>

      </div>

      {/* ── Footer ── */}
      <div className="analytics-footer">
        <button className="export-csv-btn" onClick={exportCSV}>
          ⬇ Export Full Dataset (CSV)
        </button>
        <span className="defect-count-badge">{(defects || []).length} defects recorded</span>
      </div>

    </div>
  );
}

// ── Polar orientation rose panel ─────────────────────────────────────────────

const ROSE_TYPE_COLORS = {
  '1/2<110> Perfect Loop': '#ff69b4',
  '1/2<111> Perfect Loop': '#ff69b4',
  '1/3<111> Faulted Loop': '#00ffff',
  'Edge-On':               '#ffff00',
  'Unknown':               '#888888',
};

function OrientationRosePanel({ defects }) {
  if (!defects || defects.length === 0) {
    return (
      <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem', fontSize: '0.85rem' }}>
        No orientation data yet — run an analysis with a zone axis set.
      </div>
    );
  }

  const SIZE    = 220;
  const cx      = SIZE / 2;
  const cy      = SIZE / 2;
  const R       = SIZE / 2 - 16;
  const N_BINS  = 18;   // 10° per bin, 0–180° (line orientation)

  // Accumulate bins
  const bins      = Array(N_BINS).fill(0);
  const binColors = Array(N_BINS).fill('#888888');

  defects.forEach(d => {
    if (d.angle_deg == null) return;
    let a = ((d.angle_deg % 180) + 180) % 180;
    const bi = Math.min(N_BINS - 1, Math.floor(a / (180 / N_BINS)));
    bins[bi]++;
    binColors[bi] = ROSE_TYPE_COLORS[d.type] || '#888888';
  });

  const maxBin = Math.max(...bins, 1);

  const petals = bins.flatMap((count, i) => {
    if (count === 0) return [];
    const frac   = count / maxBin;
    const r      = R * 0.12 + R * 0.88 * frac;
    const degPerBin = 180 / N_BINS;
    const aStart = (i * degPerBin) * Math.PI / 180;
    const aEnd   = ((i + 1) * degPerBin) * Math.PI / 180;

    return [0, Math.PI].map((offset, j) => {
      const a1 = aStart + offset;
      const a2 = aEnd   + offset;
      const x1 = cx + r * Math.cos(a1);
      const y1 = cy - r * Math.sin(a1);
      const x2 = cx + r * Math.cos(a2);
      const y2 = cy - r * Math.sin(a2);
      return (
        <path key={`${i}-${j}`}
          d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 0 ${x2} ${y2} Z`}
          fill={binColors[i]} fillOpacity="0.5"
          stroke={binColors[i]} strokeWidth="0.8" strokeOpacity="0.9"
        />
      );
    });
  });

  // Axis labels (0°, 45°, 90°, 135°)
  const axisLabels = [0, 45, 90, 135].map(deg => {
    const rad = deg * Math.PI / 180;
    return (
      <text key={deg}
        x={cx + (R + 10) * Math.cos(rad)}
        y={cy - (R + 10) * Math.sin(rad)}
        textAnchor="middle" dominantBaseline="central"
        fill="rgba(255,255,255,0.25)" fontSize="9" fontFamily="monospace">
        {deg}°
      </text>
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', paddingTop: '8px' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        {/* Background circles */}
        {[0.33, 0.66, 1].map(f => (
          <circle key={f} cx={cx} cy={cy} r={R * f}
            fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
        ))}
        {/* Spoke lines every 30° */}
        {Array.from({length: 6}, (_, i) => {
          const a = (i * 30) * Math.PI / 180;
          return <line key={i}
            x1={cx - R * Math.cos(a)} y1={cy + R * Math.sin(a)}
            x2={cx + R * Math.cos(a)} y2={cy - R * Math.sin(a)}
            stroke="rgba(255,255,255,0.06)" strokeWidth="1"/>;
        })}
        {petals}
        {axisLabels}
        <circle cx={cx} cy={cy} r="3.5" fill="#6366f1"/>
      </svg>
      <div style={{ fontSize: '0.72rem', color: '#64748b', textAlign: 'center', lineHeight: 1.5 }}>
        Each petal = count of loops with that orientation (±5°)<br/>
        Color = dominant loop type in that bin
      </div>
    </div>
  );
}
