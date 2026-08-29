import React from 'react';
import Panel from '../components/ui/Panel';
import StatusBadge from '../components/ui/StatusBadge';
import PipelineFlow from '../components/PipelineFlow';

export default function SystemHealthView({ connectionStatus }) {
  const services = [
    { name: 'Kafka Broker', endpoint: 'localhost:9092', status: connectionStatus === 'live' ? 'ok' : 'error' },
    { name: 'TimescaleDB', endpoint: 'localhost:5432', status: 'ok' },
    { name: 'FastAPI Backend', endpoint: 'http://localhost:8000/health', status: 'ok' },
    { name: 'Feature Extractor', endpoint: 'features.conn / features.dns', status: 'ok' },
    { name: 'Alert Sink Worker', endpoint: 'alerts -> DB', status: 'ok' },
    { name: 'WebSocket Broadcast', endpoint: 'ws://localhost:8000/ws/alerts', status: connectionStatus },
    { name: 'Grafana Analytics', endpoint: 'http://localhost:3001', status: 'ok' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PipelineFlow />

      <Panel title="SYSTEM HEALTH & SERVICE STATUS">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {services.map(s => (
            <div key={s.name} className="detector-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <StatusBadge status={s.status} label={s.status.toUpperCase()} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</span>
              </div>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                {s.endpoint}
              </span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
