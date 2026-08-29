import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import AlertSummary from './components/AlertSummary';
import ThreatFilter from './components/ThreatFilter';
import LiveFeed from './components/LiveFeed';
import AlertDetails from './components/AlertDetails';
import ThreatDistribution from './components/ThreatDistribution';
import AlertTimeline from './components/AlertTimeline';

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({ total: 0, critical: 0, high: 0, medium: 0, low: 0, by_threat: {} });
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);
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
    fetch(`${API_BASE}/alerts`)
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
          setAlerts(prev => [newAlert, ...prev]);
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

  const filteredAlerts = alerts.filter(a => {
    if (selectedFilter === 'All') return true;
    return a.threat_class === selectedFilter;
  });

  return (
    <div className="app-container">
      <Header connectionStatus={connectionStatus} />

      <main className="content">
        <AlertSummary stats={stats} />

        <ThreatFilter 
          selectedFilter={selectedFilter} 
          onSelectFilter={setSelectedFilter} 
        />

        <div style={{ display: 'grid', gridTemplateColumns: '65% 35%', gap: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <LiveFeed 
              alerts={filteredAlerts}
              selectedAlert={selectedAlert}
              onSelectAlert={setSelectedAlert}
            />

            <AlertTimeline alerts={alerts} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <AlertDetails 
              alert={selectedAlert} 
              onClose={() => setSelectedAlert(null)}
            />

            <ThreatDistribution byThreat={stats.by_threat} />
          </div>
        </div>
      </main>
    </div>
  );
}
