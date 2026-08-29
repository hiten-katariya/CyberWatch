import React from 'react';
import { Shield, ExternalLink } from 'lucide-react';

export default function Header({ connectionStatus }) {
  return (
    <header className="top-bar">
      <div className="brand">
        <Shield size={22} color="#3B82F6" />
        <span className="brand-title">PASSIVE ONE-WAY THREAT DETECTION & INTELLIGENCE PLATFORM</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <a 
          href="http://localhost:3001" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#3B82F6', textDecoration: 'none' }}
        >
          <span>GRAFANA ANALYTICS</span>
          <ExternalLink size={14} />
        </a>

        <div className="status-badge">
          <span className={`dot ${connectionStatus}`}></span>
          <span>{connectionStatus === 'live' ? 'LIVE WEBSOCKET' : connectionStatus.toUpperCase()}</span>
        </div>
      </div>
    </header>
  );
}
