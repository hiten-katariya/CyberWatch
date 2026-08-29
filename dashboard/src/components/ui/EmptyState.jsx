import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function EmptyState({ title = "NO ACTIVE ALERTS", message = "No threat anomalies detected in the current observation window." }) {
  return (
    <div className="empty-state">
      <ShieldCheck size={36} style={{ color: 'var(--status-ok)', marginBottom: 12, opacity: 0.8 }} />
      <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{title}</h4>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{message}</p>
    </div>
  );
}
