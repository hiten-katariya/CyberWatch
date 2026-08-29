import React from 'react';
import LiveFeed from '../components/LiveFeed';
import AlertDetails from '../components/AlertDetails';
import ThreatFilter from '../components/ThreatFilter';

export default function LiveAlertsView({
  alerts,
  selectedFilter,
  onSelectFilter,
  selectedAlert,
  onSelectAlert
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, letterSpacing: 0.5 }}>FULL DENSE LIVE THREAT FEED</h2>
        <span className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Showing {alerts.length} matching alerts</span>
      </div>

      <ThreatFilter selectedFilter={selectedFilter} onSelectFilter={onSelectFilter} />

      <div style={{ display: 'grid', gridTemplateColumns: '60% 40%', gap: 20 }}>
        <LiveFeed alerts={alerts} selectedAlert={selectedAlert} onSelectAlert={onSelectAlert} />
        <AlertDetails alert={selectedAlert} onClose={() => onSelectAlert(null)} />
      </div>
    </div>
  );
}
