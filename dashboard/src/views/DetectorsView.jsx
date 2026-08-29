import React from 'react';
import Panel from '../components/ui/Panel';
import DetectorStatusPanel from '../components/DetectorStatusPanel';

const DETECTOR_SPECS = [
  { id: 'recon', name: 'Reconnaissance Detector', file: 'recon.py', rule: 'Port/Host Fanout Cardinality (Ports >= 15, Hosts >= 10)', severity: 'MEDIUM' },
  { id: 'ddos', name: 'DDoS Detector', file: 'ddos.py', rule: 'SYN Flood (>100 pps), UDP Flood (>100 pps), Slowloris (>300s duration)', severity: 'CRITICAL' },
  { id: 'dga', name: 'DGA Detector', file: 'dga.py', rule: 'Shannon Entropy (>3.8), Length (>22 chars), n-gram lexical analysis', severity: 'HIGH' },
  { id: 'dns_tunnel', name: 'DNS Tunnelling Detector', file: 'dns_tunnel.py', rule: 'Query Length (>50), Label Length (>30), TXT/NULL record anomalies', severity: 'HIGH' },
  { id: 'c2_beacon', name: 'C2 Beaconing Detector', file: 'c2_beacon.py', rule: 'Inter-arrival CoV (<= 0.15), Repetition Count (>= 5)', severity: 'CRITICAL' },
  { id: 'encrypted_malware', name: 'Encrypted Malware Detector', file: 'encrypted_malware.py', rule: 'JA3 / JA3S / JA4 threat-intel blocklist matching', severity: 'HIGH' },
  { id: 'exfiltration', name: 'Bulk Exfiltration Detector', file: 'exfiltration.py', rule: 'Outbound/Inbound Byte Ratio (>= 10.0), Outbound Bytes (>= 1MB)', severity: 'HIGH' }
];

export default function DetectorsView({ byThreat = {} }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <DetectorStatusPanel byThreat={byThreat} />

      <Panel title="DETECTOR THRESHOLD & SIGNAL SPECIFICATIONS">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {DETECTOR_SPECS.map(spec => (
            <div key={spec.id} className="detector-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700 }}>{spec.name}</span>
                <span className={`sev-badge ${spec.severity.toLowerCase()}`}>{spec.severity}</span>
              </div>
              <p className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>File: pipeline/detectors/{spec.file}</p>
              <div className="json-box mono" style={{ marginTop: 8, fontSize: 11, padding: 8 }}>
                Rule: {spec.rule}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
