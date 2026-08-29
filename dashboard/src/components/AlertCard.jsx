import React from 'react';
import SeverityBadge from './ui/SeverityBadge';

export default function AlertCard({ alert, isSelected, onSelect }) {
  const sev = alert.severity || 'low';
  const threat = (alert.threat_class || 'unknown').toUpperCase();
  const pattern = alert.evidence?.pattern || 'Anomaly';
  const timeAgo = Math.max(0, Math.round((new Date() - new Date(alert.timestamp)) / 1000));
  const timeStr = timeAgo < 60 ? `${timeAgo}s ago` : `${Math.round(timeAgo / 60)}m ago`;

  return (
    <div 
      className={`alert-card ${isSelected ? 'selected' : ''}`} 
      onClick={() => onSelect(alert)}
    >
      <div className={`sev-bar ${sev}`} />
      <div className="alert-body">
        <div className="alert-top">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SeverityBadge severity={sev} />
            <span className="threat-tag mono">{threat}</span>
          </div>
          <span className="timestamp mono">{timeStr}</span>
        </div>

        <div className="flow-info mono">
          <span>{alert.flow_identifier?.src_ip}:{alert.flow_identifier?.src_port}</span>
          <span style={{ color: 'var(--text-secondary)' }}>─────────→</span>
          <span>{alert.flow_identifier?.dst_ip}:{alert.flow_identifier?.dst_port}</span>
          <span className="proto-pill">[{alert.flow_identifier?.proto?.toUpperCase()}]</span>
        </div>

        <div className="evidence-summary mono">
          <strong>Pattern:</strong> {pattern} | {JSON.stringify(alert.evidence)}
        </div>

        <div className="alert-meta mono">
          <span>Confidence: {(alert.confidence * 100).toFixed(0)}%</span>
          <span>•</span>
          <span>Sensor: {alert.sensor_id}</span>
          <span>•</span>
          <span>ID: {alert.alert_id?.substring(0, 8)}...</span>
        </div>
      </div>
    </div>
  );
}
