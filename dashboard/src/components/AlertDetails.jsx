import React, { useState } from 'react';
import { X, Copy, Check, ShieldAlert } from 'lucide-react';
import SeverityBadge from './ui/SeverityBadge';

export default function AlertDetails({ alert, onClose }) {
  const [copiedKey, setCopiedKey] = useState(null);

  if (!alert) {
    return (
      <div className="details-panel empty">
        <ShieldAlert size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
        <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>NO ALERT SELECTED</h4>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
          Select an alert from the live stream to inspect detailed network evidence and forensic attributes.
        </p>
      </div>
    );
  }

  const handleCopy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  return (
    <div className="details-panel">
      <div className="details-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SeverityBadge severity={alert.severity} />
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>{alert.threat_class?.toUpperCase()} DETECTED</h3>
        </div>
        <button onClick={onClose} className="close-btn"><X size={16} /></button>
      </div>

      <div className="details-body">
        {/* Basic Info */}
        <div className="detail-section">
          <div className="section-hdr">DETECTION SUMMARY</div>
          <table className="meta-table mono">
            <tbody>
              <tr>
                <td>Alert ID:</td>
                <td style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{alert.alert_id}</span>
                  <button onClick={() => handleCopy(alert.alert_id, 'id')} className="copy-btn">
                    {copiedKey === 'id' ? <Check size={12} color="var(--status-ok)" /> : <Copy size={12} />}
                  </button>
                </td>
              </tr>
              <tr><td>Timestamp:</td><td>{alert.timestamp}</td></tr>
              <tr><td>Threat Class:</td><td style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{alert.threat_class?.toUpperCase()}</td></tr>
              <tr><td>Confidence:</td><td>{(alert.confidence * 100).toFixed(0)}%</td></tr>
              <tr><td>Sensor ID:</td><td>{alert.sensor_id}</td></tr>
            </tbody>
          </table>
        </div>

        {/* Network Flow */}
        <div className="detail-section">
          <div className="section-hdr">NETWORK FLOW</div>
          <table className="meta-table mono">
            <tbody>
              <tr>
                <td>Source IP:</td>
                <td style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{alert.flow_identifier?.src_ip}</span>
                  <button onClick={() => handleCopy(alert.flow_identifier?.src_ip, 'src')} className="copy-btn">
                    {copiedKey === 'src' ? <Check size={12} color="var(--status-ok)" /> : <Copy size={12} />}
                  </button>
                </td>
              </tr>
              <tr><td>Source Port:</td><td>{alert.flow_identifier?.src_port}</td></tr>
              <tr>
                <td>Destination IP:</td>
                <td style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{alert.flow_identifier?.dst_ip}</span>
                  <button onClick={() => handleCopy(alert.flow_identifier?.dst_ip, 'dst')} className="copy-btn">
                    {copiedKey === 'dst' ? <Check size={12} color="var(--status-ok)" /> : <Copy size={12} />}
                  </button>
                </td>
              </tr>
              <tr><td>Destination Port:</td><td>{alert.flow_identifier?.dst_port}</td></tr>
              <tr><td>Protocol:</td><td>{alert.flow_identifier?.proto?.toUpperCase()}</td></tr>
            </tbody>
          </table>
        </div>

        {/* Forensic Evidence */}
        <div className="detail-section">
          <div className="section-hdr" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>FORENSIC EVIDENCE</span>
            <button onClick={() => handleCopy(JSON.stringify(alert.evidence, null, 2), 'ev')} className="copy-btn">
              {copiedKey === 'ev' ? <Check size={12} color="var(--status-ok)" /> : <Copy size={12} />}
            </button>
          </div>
          <div className="json-box mono">
            <pre>{JSON.stringify(alert.evidence, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
