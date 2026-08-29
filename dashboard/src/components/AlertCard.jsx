import React from 'react';

export default function AlertCard({ alert, isSelected, onSelect }) {
  const sev = alert.severity || 'low';
  const threat = (alert.threat_class || 'unknown').toUpperCase();
  const pattern = alert.evidence?.pattern || '';

  return (
    <div 
      className={`alert-card ${isSelected ? 'selected' : ''}`} 
      onClick={() => onSelect(alert)}
      style={{ cursor: 'pointer' }}
    >
      <div className={`sev-bar ${sev}`} />
      <div className="alert-body">
        <div className="alert-top">
          <span className="threat-tag">
            {threat} · {sev.toUpperCase()} ({(alert.confidence * 100).toFixed(0)}% CONF)
          </span>
          <span className="timestamp mono">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </span>
        </div>

        <div className="flow-info mono">
          <span>{alert.flow_identifier?.src_ip}:{alert.flow_identifier?.src_port}</span>
          <span style={{ color: 'var(--text-secondary)' }}>→</span>
          <span>{alert.flow_identifier?.dst_ip}:{alert.flow_identifier?.dst_port}</span>
          <span style={{ fontSize: 12, color: 'var(--accent-primary)', marginLeft: 8 }}>
            [{alert.flow_identifier?.proto?.toUpperCase()}]
          </span>
        </div>

        <div className="evidence-box">
          <strong>Pattern:</strong> {pattern || 'Generic Anomaly'} | {JSON.stringify(alert.evidence)}
        </div>

        <div className="alert-id mono">
          ALERT ID: {alert.alert_id} | SENSOR: {alert.sensor_id}
        </div>
      </div>
    </div>
  );
}
