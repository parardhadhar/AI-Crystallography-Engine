import React from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DynamicGraph({ config }) {
  if (!config || !config.data || !config.type) {
    return <div style={{ color: '#EF4444', fontSize: '0.75rem' }}>Invalid graph configuration provided by AI.</div>;
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: '#111', border: '1px solid #333', padding: '10px', borderRadius: '4px', color: '#fff' }}>
          <p style={{ margin: 0, fontSize: '12px', color: '#888' }}>{label}</p>
          <p style={{ margin: 0, fontSize: '14px', fontWeight: 'bold', color: '#00e5ff' }}>
            {payload[0].value}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 250, background: '#050505', border: '1px solid #222', borderRadius: '8px', padding: '1rem', marginTop: '1rem', marginBottom: '1rem' }}>
      <h4 style={{ color: '#fff', fontSize: '0.875rem', marginBottom: '1rem', textAlign: 'center', fontWeight: 500 }}>
        {config.title || 'Data Visualization'}
      </h4>
      <ResponsiveContainer width="100%" height="80%">
        {config.type === 'bar' ? (
          <BarChart data={config.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
            <XAxis dataKey="name" stroke="#888" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#888" fontSize={11} tickLine={false} axisLine={false} width={40} />
            <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.05)'}} />
            <Bar dataKey="value" fill="#00e5ff" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        ) : (
          <LineChart data={config.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
            <XAxis dataKey="name" stroke="#888" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#888" fontSize={11} tickLine={false} axisLine={false} width={40} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="value" stroke="#00e5ff" strokeWidth={3} dot={{ r: 4, fill: '#00e5ff', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
