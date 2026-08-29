import React from 'react';

const THREAT_CLASSES = [
  "All",
  "recon",
  "ddos",
  "dga",
  "dns_tunnel",
  "c2_beacon",
  "encrypted_malware",
  "exfiltration"
];

export default function ThreatFilter({ selectedFilter, onSelectFilter }) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
      {THREAT_CLASSES.map(tc => (
        <button
          key={tc}
          onClick={() => onSelectFilter(tc)}
          className={`chip-button ${selectedFilter === tc ? 'active' : ''}`}
        >
          {tc.toUpperCase().replace('_', ' ')}
        </button>
      ))}
    </div>
  );
}
