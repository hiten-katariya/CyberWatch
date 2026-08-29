import React, { useState, useEffect } from 'react';
import { Shield, Activity, Radio, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`;
  
  const WS_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'ws://localhost:8000/ws/alerts' 
    : `ws://${window.location.hostname}:8000/ws/alerts`;

  // Fetch initial alerts
  useEffect(() => {
    fetch(`${API_BASE}/alerts`)
      .then(res => res.json())
      .then(data => {
        if (data && data.alerts) {
          setAlerts(data.alerts);
        }
      })
      .catch(err => console.error("Initial alerts fetch error:", err));
  }, [API_BASE]);

  // WebSocket Live Connection
  useEffect(() => {
    let ws = null;
    let connectTimer = null;

    const connectWS = () => {
      setConnectionStatus('connecting');
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log("WebSocket connected to", WS_URL);
        setConnectionStatus('live');
      };

      ws.onmessage = (event) => {
        try {
          const newAlert = JSON.parse(event.data);
          console.log("Live WebSocket Alert Received:", newAlert);
          setAlerts(prev => [newAlert, ...prev]);
        } catch (e) {
          console.error("Error parsing WS message:", e);
        }
      };

      ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
        setConnectionStatus('disconnected');
      };

      ws.onclose = () => {
        console.warn("WebSocket disconnected. Reconnecting in 3s...");
        setConnectionStatus('disconnected');
        connectTimer = setTimeout(connectWS, 3000);
      };
    };

    connectWS();

    return () => {
      if (ws) ws.close();
      if (connectTimer) clearTimeout(connectTimer);
    };
  }, [WS_URL]);

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <header className="top-bar">
        <div className="brand">
          <Shield size={20} color="#3B82F6" />
          <span className="brand-title">PASSIVE THREAT DETECTION PLATFORM</span>
        </div>

        <div className="status-badge">
          <span className={`dot ${connectionStatus}`}></span>
          <span>{connectionStatus === 'live' ? 'LIVE WEBSOCKET' : connectionStatus.toUpperCase()}</span>
        </div>
      </header>

      {/* Main Content Feed */}
      <main className="content">
        <div className="feed-header">
          <h2 className="section-title">Phase 1 Pipeline Alert Feed</h2>
          <span className="alert-counter">Total Alerts: {alerts.length}</span>
        </div>

        {alerts.length === 0 ? (
          <div className="empty-state">
            <Radio size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
            <p>Waiting for Phase 1 benign traffic & placeholder alert...</p>
            <p className="mono" style={{ fontSize: 12, marginTop: 8 }}>
              Run iperf3 generator → Zeek → Kafka → Placeholder Detector → Alert Sink
            </p>
          </div>
        ) : (
          <div className="alert-list">
            {alerts.map((alert, idx) => (
              <div key={alert.alert_id || idx} className="alert-card">
                <div className={`sev-bar ${alert.severity || 'low'}`} />
                <div className="alert-body">
                  <div className="alert-top">
                    <span className="threat-tag">
                      {alert.threat_class} · {alert.severity} ({(alert.confidence * 100).toFixed(0)}% CONF)
                    </span>
                    <span className="timestamp mono">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="flow-info mono">
                    <span>{alert.flow_identifier?.src_ip}:{alert.flow_identifier?.src_port}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>→</span>
                    <span>{alert.flow_identifier?.dst_ip}:{alert.flow_identifier?.dst_port}</span>
                    <span style={{ fontSize: 12, color: 'var(--accent-primary)', marginLeft: 8 }}>
                      [{alert.flow_identifier?.proto?.toUpperCase()}]
                    </span>
                  </div>

                  <div className="evidence-box">
                    <strong>Evidence:</strong> {alert.evidence?.message || JSON.stringify(alert.evidence)}
                  </div>

                  <div className="alert-id mono">
                    ALERT ID: {alert.alert_id} | SENSOR: {alert.sensor_id}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
