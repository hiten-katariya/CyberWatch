import React from 'react';
import { Shield, ExternalLink, Bell } from 'lucide-react';
import StatusBadge from './ui/StatusBadge';
import SearchInput from './ui/SearchInput';

export default function Header({ connectionStatus, globalSearch, onSearchChange }) {
  return (
    <header className="top-bar">
      <div className="brand">
        <Shield size={22} color="var(--accent-primary)" />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="brand-title">THREATPIPE</span>
          <span className="brand-subtitle mono">Network Threat Intelligence Platform</span>
        </div>
      </div>

      <div style={{ flex: 1, maxW: 360, margin: '0 24px' }}>
        <SearchInput value={globalSearch} onChange={onSearchChange} />
      </div>

      <div className="header-actions">
        <div className="status-group">
          <StatusBadge status={connectionStatus === 'live' ? 'ok' : 'error'} label="SYSTEM OPERATIONAL" />
          <StatusBadge status={connectionStatus === 'live' ? 'ok' : 'warning'} label="KAFKA" />
          <StatusBadge status={connectionStatus === 'live' ? 'ok' : 'warning'} label="API" />
          <StatusBadge status={connectionStatus} label={connectionStatus.toUpperCase()} />
        </div>

        <a 
          href="http://localhost:3001" 
          target="_blank" 
          rel="noopener noreferrer"
          className="external-link-btn"
          title="Open Grafana Operational Analytics"
        >
          <span>GRAFANA</span>
          <ExternalLink size={13} />
        </a>

        <div className="user-profile mono">
          <Bell size={15} color="var(--text-secondary)" />
          <span>ANALYST</span>
        </div>
      </div>
    </header>
  );
}
