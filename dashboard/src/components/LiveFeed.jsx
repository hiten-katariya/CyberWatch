import React from 'react';
import AlertCard from './AlertCard';

export default function LiveFeed({ alerts, selectedAlert, onSelectAlert }) {
  return (
    <div className="card-panel" style={{ minHeight: 400 }}>
      <h3 className="card-title" style={{ marginBottom: 12 }}>LIVE ALERT FEED</h3>
      {alerts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
          <p className="mono">No matching alerts in stream...</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {alerts.map(a => (
            <AlertCard
              key={a.alert_id}
              alert={a}
              isSelected={selectedAlert?.alert_id === a.alert_id}
              onSelect={onSelectAlert}
            />
          ))}
        </div>
      )}
    </div>
  );
}
