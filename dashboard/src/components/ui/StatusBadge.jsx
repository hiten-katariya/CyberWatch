import React from 'react';

export default function StatusBadge({ status = 'ok', label }) {
  const statusClass = status === 'ok' || status === 'healthy' || status === 'live' 
    ? 'healthy' 
    : status === 'warning' || status === 'degraded' 
    ? 'warning' 
    : 'error';

  return (
    <div className="status-badge">
      <span className={`dot ${statusClass}`} />
      <span className="mono" style={{ fontSize: 11, fontWeight: 600 }}>
        {label || status.toUpperCase()}
      </span>
    </div>
  );
}
