import React from 'react';

export default function MetricCard({ label, value, severity, subtitle, icon: Icon }) {
  const borderCol = severity === 'critical' 
    ? 'var(--sev-critical)' 
    : severity === 'high' 
    ? 'var(--sev-high)' 
    : severity === 'medium' 
    ? 'var(--sev-medium)' 
    : severity === 'low' 
    ? 'var(--sev-low)' 
    : 'var(--accent-primary)';

  return (
    <div className="metric-card" style={{ borderLeft: `4px solid ${borderCol}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="metric-label">{label}</span>
        {Icon && <Icon size={16} color="var(--text-secondary)" />}
      </div>
      <div className="metric-value mono">{value !== undefined ? value : '0'}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );
}
