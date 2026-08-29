import React from 'react';

export default function AlertTimeline({ alerts }) {
  // Simple histogram of alerts by minute
  const minuteCounts = {};
  alerts.forEach(a => {
    try {
      const min = new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      minuteCounts[min] = (minuteCounts[min] || 0) + 1;
    } catch (e) {}
  });

  const timeKeys = Object.keys(minuteCounts).reverse().slice(0, 15).reverse();
  const maxCount = Math.max(...Object.values(minuteCounts), 1);

  return (
    <div className="card-panel">
      <h3 className="card-title">ALERT TIMELINE (LAST 15 BUCKETS)</h3>
      {timeKeys.length === 0 ? (
        <p className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Awaiting alert stream...</p>
      ) : (
        <div style={{ display: 'flex', alignItems: 'flex-end', height: 100, gap: 12, paddingTop: 16 }}>
          {timeKeys.map(time => {
            const cnt = minuteCounts[time];
            const heightPct = Math.max((cnt / maxCount) * 100, 10);
            return (
              <div key={time} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <div style={{ height: `${heightPct}%`, width: '100%', background: 'var(--accent-primary)', borderRadius: '4px 4px 0 0' }} />
                <span style={{ fontSize: 10, color: 'var(--text-secondary)' }} className="mono">{time}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
