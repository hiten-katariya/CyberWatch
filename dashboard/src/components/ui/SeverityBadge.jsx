import React from 'react';
import { AlertOctagon, AlertTriangle, AlertCircle, Info } from 'lucide-react';

export default function SeverityBadge({ severity = 'low' }) {
  const s = severity.toLowerCase();
  const getIcon = () => {
    switch (s) {
      case 'critical': return <AlertOctagon size={12} />;
      case 'high': return <AlertTriangle size={12} />;
      case 'medium': return <AlertCircle size={12} />;
      default: return <Info size={12} />;
    }
  };

  return (
    <span className={`sev-badge ${s}`}>
      {getIcon()}
      <span>{s.toUpperCase()}</span>
    </span>
  );
}
