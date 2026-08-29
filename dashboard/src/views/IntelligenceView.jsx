import React from 'react';
import Panel from '../components/ui/Panel';
import StatusBadge from '../components/ui/StatusBadge';

export default function IntelligenceView() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Threat Intelligence Feed Status */}
        <Panel title="LOCAL THREAT INTELLIGENCE FEEDS">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>JA3 / JA3S TLS Blocklist Feed</span>
              <StatusBadge status="ok" label="ACTIVE" />
            </div>
            <table className="meta-table mono">
              <tbody>
                <tr><td>Feed Source:</td><td>Config-provisioned local blocklist</td></tr>
                <tr><td>Network Access:</td><td>Isolated (No outbound internet call from lab-net)</td></tr>
                <tr><td>Active Hashes:</td><td>3 blocklisted JA3 fingerprints loaded</td></tr>
                <tr><td>Last Updated:</td><td>2026-08-29 17:44:00 UTC</td></tr>
              </tbody>
            </table>
          </div>
        </Panel>

        {/* ML Model Status */}
        <Panel title="MACHINE LEARNING MODEL STATUS">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>DGA Classifier (LightGBM)</span>
              <StatusBadge status="ok" label="RULE-BASED GATE ACTIVE" />
            </div>
            <table className="meta-table mono">
              <tbody>
                <tr><td>Model Type:</td><td>LightGBM / Shannon Entropy Fallback</td></tr>
                <tr><td>Fallback Gate:</td><td>Entropy (&gt;3.8) &amp; Length (&gt;22) active</td></tr>
                <tr><td>Safety Status:</td><td>Model unavailabilities do not interrupt detection</td></tr>
                <tr><td>Version:</td><td>1.0.0-rule-fallback</td></tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <Panel title="JA3 TLS FINGERPRINT THREAT-INTEL INDICATORS">
        <table className="meta-table mono">
          <thead>
            <tr style={{ color: 'var(--text-secondary)' }}>
              <th style={{ textAlign: 'left', padding: '4px 0' }}>FINGERPRINT / HASH</th>
              <th style={{ textAlign: 'left', padding: '4px 0' }}>TYPE</th>
              <th style={{ textAlign: 'left', padding: '4px 0' }}>SEVERITY</th>
              <th style={{ textAlign: 'left', padding: '4px 0' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>e7d705a3286e19ea42f587b344ee6865</td>
              <td>JA3 TLS</td>
              <td><span className="sev-badge high">HIGH</span></td>
              <td>BLOCKLISTED</td>
            </tr>
            <tr>
              <td>6732f5ee9e07214161014cc672c9775f</td>
              <td>JA3 TLS</td>
              <td><span className="sev-badge high">HIGH</span></td>
              <td>BLOCKLISTED</td>
            </tr>
            <tr>
              <td>ada301376e18c44be079577c21c4f4a6</td>
              <td>JA3 TLS</td>
              <td><span className="sev-badge high">HIGH</span></td>
              <td>BLOCKLISTED</td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
