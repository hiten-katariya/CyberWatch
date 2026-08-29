import React from 'react';
import Panel from './ui/Panel';
import StatusBadge from './ui/StatusBadge';
import { ArrowRight } from 'lucide-react';

const STAGES = [
  { name: 'Zeek Sensor', type: 'Mirror / Capture', status: 'healthy' },
  { name: 'Ingest Adapter', type: 'TSV/JSON Normalizer', status: 'healthy' },
  { name: 'Kafka Bus', type: 'events.* / features.*', status: 'healthy' },
  { name: 'Feature Layer', type: 'Window Extractor', status: 'healthy' },
  { name: '7 Detectors', type: 'Rule + ML Rules', status: 'healthy' },
  { name: 'Alert Sink', type: 'Worker', status: 'healthy' },
  { name: 'TimescaleDB', type: 'Storage', status: 'healthy' },
  { name: 'FastAPI Backend', type: 'REST & WS', status: 'healthy' },
  { name: 'React SOC UI', type: 'Analyst Interface', status: 'healthy' }
];

export default function PipelineFlow() {
  return (
    <Panel title="PASSIVE ONE-WAY PIPELINE STATUS">
      <div className="pipeline-flow-container">
        {STAGES.map((s, idx) => (
          <React.Fragment key={s.name}>
            <div className="pipeline-node">
              <span className="node-name">{s.name}</span>
              <span className="node-type mono">{s.type}</span>
              <StatusBadge status={s.status} label="OPERATIONAL" />
            </div>
            {idx < STAGES.length - 1 && (
              <ArrowRight size={14} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
            )}
          </React.Fragment>
        ))}
      </div>
    </Panel>
  );
}
