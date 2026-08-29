import React, { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import OverviewView from './views/OverviewView';
import LiveAlertsView from './views/LiveAlertsView';
import DetectorsView from './views/DetectorsView';
import IntelligenceView from './views/IntelligenceView';
import SystemHealthView from './views/SystemHealthView';

export default function App() {
  const [activeView, setActiveView] = useState('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({ total: 0, critical: 0, high: 0, medium: 0, low: 0, by_threat: {} });
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [globalSearch, setGlobalSearch] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('connecting');

  const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`;
  
  const WS_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'ws://localhost:8000/ws/alerts' 
    : `ws://${window.location.hostname}:8000/ws/alerts`;

  const fetchStats = () => {
    fetch(`${API_BASE}/alerts/stats`)
      .then(res => res.json())
      .then(data => { if (data) setStats(data); })
      .catch(err => console.error("Stats fetch error:", err));
  };

  const fetchAlerts = () => {
    fetch(`${API_BASE}/alerts?limit=200`)
      .then(res => res.json())
      .then(data => { if (data && data.alerts) setAlerts(data.alerts); })
      .catch(err => console.error("Alerts fetch error:", err));
  };

  useEffect(() => {
    fetchStats();
    fetchAlerts();
  }, [API_BASE]);

  useEffect(() => {
    let ws = null;
    let timer = null;

    const connect = () => {
      setConnectionStatus('connecting');
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setConnectionStatus('live');
      };

      ws.onmessage = (event) => {
        try {
          const newAlert = JSON.parse(event.data);
          setAlerts(prev => [newAlert, ...prev.slice(0, 300)]);
          fetchStats();
        } catch (e) {}
      };

      ws.onerror = () => {
        setConnectionStatus('disconnected');
      };

      ws.onclose = () => {
        setConnectionStatus('disconnected');
        timer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (timer) clearTimeout(timer);
    };
  }, [WS_URL]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter(a => {
      if (selectedFilter !== 'All' && a.threat_class !== selectedFilter) {
        return false;
      }
      if (globalSearch.trim() !== '') {
        const q = globalSearch.toLowerCase();
        const src = a.flow_identifier?.src_ip || '';
        const dst = a.flow_identifier?.dst_ip || '';
        const id = a.alert_id || '';
        const threat = a.threat_class || '';
        const ev = JSON.stringify(a.evidence || {});
        return src.toLowerCase().includes(q) || 
               dst.toLowerCase().includes(q) || 
               id.toLowerCase().includes(q) || 
               threat.toLowerCase().includes(q) ||
               ev.toLowerCase().includes(q);
      }
      return true;
    });
  }, [alerts, selectedFilter, globalSearch]);

  const renderActiveView = () => {
    switch (activeView) {
      case 'overview':
        return (
          <OverviewView 
            alerts={filteredAlerts}
            stats={stats}
            selectedFilter={selectedFilter}
            onSelectFilter={setSelectedFilter}
            selectedAlert={selectedAlert}
            onSelectAlert={setSelectedAlert}
          />
        );
      case 'live_alerts':
        return (
          <LiveAlertsView 
            alerts={filteredAlerts}
            selectedFilter={selectedFilter}
            onSelectFilter={setSelectedFilter}
            selectedAlert={selectedAlert}
            onSelectAlert={setSelectedAlert}
          />
        );
      case 'detectors':
        return <DetectorsView byThreat={stats.by_threat} />;
      case 'intelligence':
        return <IntelligenceView />;
      case 'system_health':
        return <SystemHealthView connectionStatus={connectionStatus} />;
      default:
        return null;
    }
  };

  return (
    <div className="app-shell">
      <Header 
        connectionStatus={connectionStatus} 
        globalSearch={globalSearch}
        onSearchChange={setGlobalSearch}
      />
      
      <div className="shell-body">
        <Sidebar 
          activeView={activeView}
          onViewChange={setActiveView}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        <main className="main-content">
          {renderActiveView()}
        </main>
      </div>
    </div>
  );
}
