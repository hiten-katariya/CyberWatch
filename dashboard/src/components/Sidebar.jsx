import React from 'react';
import { LayoutDashboard, Radio, Shield, Cpu, Activity, Cpu as CpuIcon, Settings, ChevronLeft, ChevronRight } from 'lucide-react';

export default function Sidebar({ activeView, onViewChange, collapsed, onToggleCollapse }) {
  const navItems = [
    { section: 'OVERVIEW', items: [
      { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'live_alerts', label: 'Live Alerts', icon: Radio },
    ]},
    { section: 'DETECTION', items: [
      { id: 'detectors', label: 'Detectors', icon: Shield },
    ]},
    { section: 'INTELLIGENCE', items: [
      { id: 'intelligence', label: 'Threat Intel & Models', icon: Cpu },
    ]},
    { section: 'SYSTEM', items: [
      { id: 'system_health', label: 'Pipeline & System Health', icon: Activity },
    ]}
  ];

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <button onClick={onToggleCollapse} className="collapse-toggle" title="Toggle Sidebar">
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(grp => (
          <div key={grp.section} className="nav-group">
            {!collapsed && <div className="nav-section-title">{grp.section}</div>}
            {grp.items.map(item => {
              const Icon = item.icon;
              const isActive = activeView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onViewChange(item.id)}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={16} />
                  {!collapsed && <span>{item.label}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && <div className="version-info mono">v2.0.0 · SIH ISOLATED LAB</div>}
      </div>
    </aside>
  );
}
