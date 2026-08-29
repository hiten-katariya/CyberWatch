import React from 'react';
import { X, ShieldAlert } from 'lucide-react';

export default function AlertDetails({ alert, onClose }) {
  if (!alert) {
    return (
      <div className="details-panel empty">
        <ShieldAlert size={36} style={{ opacity: 0.3, marginBottom: 12 }} />
        <p>Select an alert from the live feed to inspect forensic evidence.</p>
      </div>
    );
  }

  return (
    <div className="details-panel">
      <div className="details-header">
        <h3>Alert Evidence Drawer</h3>
        <button onClick={onClose} className="close-btn"><X size={18} /></button>
      </div>

      <div className="details-body">
        <div className="detail-section">
          <h4>BASIC METADATA</h4>
          <table className="meta-table mono">
            <tbody>
              <tr><td>Alert ID:</td><td>{alert.alert_id}</td></tr>
              <tr><td>Timestamp:</td><td>{alert.timestamp}</td></tr>
              <tr><td>Threat Class:</td><td style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{alert.threat_class?.toUpperCase()}</td></tr>
              <tr><td>Severity:</td><td><span className={`sev-badge ${alert.severity}`}>{alert.severity?.toUpperCase()}</span></td></tr>
              <tr><td>Confidence:</td><td>{(alert.confidence * 100).toFixed(0)}%</td></tr>
              <tr><td>Sensor ID:</td><td>{alert.sensor_id}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="detail-section">
          <h4>FLOW TUPLE</h4>
          <table className="meta-table mono">
            <tbody>
              <tr><td>Source IP:</td><td>{alert.flow_identifier?.src_ip}</td></tr>
              <tr><td>Source Port:</td><td>{alert.flow_identifier?.src_port}</td></tr>
              <tr><td>Destination IP:</td><td>{alert.flow_identifier?.dst_ip}</td></tr>
              <tr><td>Destination Port:</td><td>{alert.flow_identifier?.dst_port}</td></tr>
              <tr><td>Protocol:</td><td>{alert.flow_identifier?.proto?.toUpperCase()}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="detail-section">
          <h4>FORENSIC EVIDENCE</h4>
          <div className="json-box mono">
            <pre>{JSON.stringify(alert.evidence, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
