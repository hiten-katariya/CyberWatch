import React from 'react';

export default function ThreatDistribution({ byThreat }) {
  const entries = Object.entries(byThreat || {});
  const maxVal = Math.max(...entries.map(e => e[1]), 1);

  return (
    <div className="card-panel">
      <h3 className="card-title">THREAT DISTRIBUTION</h3>
      {entries.length === 0 ? (
        <p className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>No threat data recorded yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {entries.map(([threat, count]) => {
            const pct = Math.round((count / maxVal) * 100);
            return (
              <div key={threat} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }} className="mono">
                  <span>{threat.toUpperCase()}</span>
                  <span>{count}</span>
                </div>
                <div style={{ background: 'var(--bg-surface-raised)', height: 8, borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, background: 'var(--accent-primary)', height: '100%' }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
