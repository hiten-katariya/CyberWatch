import React from 'react';
import Panel from './ui/Panel';
import StatusBadge from './ui/StatusBadge';

const DETECTORS = [
  { id: 'recon', label: 'Reconnaissance', module: 'recon.py', input: 'features.conn' },
  { id: 'ddos', label: 'DDoS (SYN / UDP / Slowloris)', module: 'ddos.py', input: 'features.conn' },
  { id: 'dga', label: 'DGA Detection', module: 'dga.py', input: 'events.dns' },
  { id: 'dns_tunnel', label: 'DNS Tunnelling', module: 'dns_tunnel.py', input: 'events.dns' },
  { id: 'c2_beacon', label: 'C2 Beaconing', module: 'c2_beacon.py', input: 'features.conn' },
  { id: 'encrypted_malware', label: 'Encrypted Malware', module: 'encrypted_malware.py', input: 'events.tls' },
  { id: 'exfiltration', label: 'Bulk Exfiltration', module: 'exfiltration.py', input: 'features.conn' }
];

export default function DetectorStatusPanel({ byThreat = {} }) {
  return (
    <Panel title="DETECTOR MODULE STATUS">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {DETECTORS.map(d => {
          const count = byThreat[d.id] || 0;
          return (
            <div key={d.id} className="detector-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StatusBadge status="ok" label="ACTIVE" />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{d.label}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }} className="mono">
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Input: {d.input}</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-primary)' }}>{count} Alerts</span>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
