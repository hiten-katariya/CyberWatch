import React from 'react';
import MetricCard from '../components/ui/MetricCard';
import LiveFeed from '../components/LiveFeed';
import AlertDetails from '../components/AlertDetails';
import ThreatDistribution from '../components/ThreatDistribution';
import AlertTimeline from '../components/AlertTimeline';
import DetectorStatusPanel from '../components/DetectorStatusPanel';
import PipelineFlow from '../components/PipelineFlow';
import ThreatFilter from '../components/ThreatFilter';
import { AlertOctagon, AlertTriangle, AlertCircle, Radio, Shield } from 'lucide-react';

export default function OverviewView({
  alerts,
  stats,
  selectedFilter,
  onSelectFilter,
  selectedAlert,
  onSelectAlert
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
        <MetricCard label="ACTIVE THREATS" value={stats.total} severity="critical" icon={Shield} />
        <MetricCard label="CRITICAL" value={stats.critical} severity="critical" icon={AlertOctagon} />
        <MetricCard label="HIGH" value={stats.high} severity="high" icon={AlertTriangle} />
        <MetricCard label="MEDIUM" value={stats.medium} severity="medium" icon={AlertCircle} />
        <MetricCard label="LOW" value={stats.low} severity="low" icon={Radio} />
      </div>

      {/* Threat Filter Pills */}
      <ThreatFilter selectedFilter={selectedFilter} onSelectFilter={onSelectFilter} />

      {/* Main Grid: 65% Feed/Timeline, 35% Evidence Drawer & Threat Analytics */}
      <div style={{ display: 'grid', gridTemplateColumns: '65% 35%', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <LiveFeed alerts={alerts} selectedAlert={selectedAlert} onSelectAlert={onSelectAlert} />
          <AlertTimeline alerts={alerts} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <AlertDetails alert={selectedAlert} onClose={() => onSelectAlert(null)} />
          <ThreatDistribution byThreat={stats.by_threat} />
          <DetectorStatusPanel byThreat={stats.by_threat} />
        </div>
      </div>

      {/* Pipeline Flow Section */}
      <PipelineFlow />
    </div>
  );
}
