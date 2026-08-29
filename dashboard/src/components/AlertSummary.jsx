import React from 'react';

export default function AlertSummary({ stats }) {
  const { total = 0, critical = 0, high = 0, medium = 0, low = 0 } = stats || {};

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 20 }}>
      <div className="summary-card" style={{ borderLeft: '4px solid var(--sev-critical)' }}>
        <span className="summary-label">CRITICAL</span>
        <span className="summary-val" style={{ color: 'var(--sev-critical)' }}>{critical}</span>
      </div>

      <div className="summary-card" style={{ borderLeft: '4px solid var(--sev-high)' }}>
        <span className="summary-label">HIGH</span>
        <span className="summary-val" style={{ color: 'var(--sev-high)' }}>{high}</span>
      </div>

      <div className="summary-card" style={{ borderLeft: '4px solid var(--sev-medium)' }}>
        <span className="summary-label">MEDIUM</span>
        <span className="summary-val" style={{ color: 'var(--sev-medium)' }}>{medium}</span>
      </div>

      <div className="summary-card" style={{ borderLeft: '4px solid var(--sev-low)' }}>
        <span className="summary-label">LOW</span>
        <span className="summary-val" style={{ color: 'var(--sev-low)' }}>{low}</span>
      </div>

      <div className="summary-card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
        <span className="summary-label">TOTAL ALERTS</span>
        <span className="summary-val">{total}</span>
      </div>
    </div>
  );
}
