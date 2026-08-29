# Frontend Design Document
## SOC Analyst Dashboard — Passive Threat Detection Platform

**Version:** 1.0 · **Companion to:** PRD v1.0, Technical Design Document v1.0

---

## 1. Purpose

This document specifies the visual design system, information architecture, interaction patterns, and component specifications for the analyst-facing dashboard. It is the reference for frontend implementation and ensures visual/interaction consistency across the application.

---

## 2. Design Principles

1. **Signal over noise.** An analyst scanning the screen for 2 seconds should immediately know if something critical is happening. Severity must be legible before content is read.
2. **Evidence-first.** Every alert must let the analyst answer "why was this flagged?" within one click — never buried behind multiple navigation steps.
3. **Live by default.** The system is a streaming platform; the UI must never feel static. New data arrives without user action.
4. **Density with clarity.** SOC operators work with high alert volumes. The UI favors compact, scannable rows over generous whitespace, but never at the cost of legibility.
5. **Trustworthy, not decorative.** This is operational security tooling. Motion, color, and iconography serve function (drawing attention to state changes) — not branding flourish.

---

## 3. Visual Identity

### 3.1 Theme

Dark theme, mandatory (not just default) — reduces eye strain in 24/7 SOC environments displayed on wall monitors, and is the visual convention analysts already expect from tools like Splunk, Grafana, and Kibana.

### 3.2 Color System

| Token | Hex | Usage |
|---|---|---|
| `bg-base` | `#0B0F19` | App background |
| `bg-surface` | `#141A29` | Cards, panels |
| `bg-surface-raised` | `#1C2438` | Modals, drawers, hover states |
| `border-subtle` | `#2A3350` | Dividers, card borders |
| `text-primary` | `#E6E9F0` | Primary text |
| `text-secondary` | `#8B93A8` | Metadata, timestamps, labels |
| `accent-primary` | `#3B82F6` | Interactive elements, links, active states |

**Severity palette (fixed, never reused for anything else in the UI):**

| Severity | Hex | Usage |
|---|---|---|
| Critical | `#EF4444` | Left border, badge, icon |
| High | `#F97316` | Left border, badge, icon |
| Medium | `#EAB308` | Left border, badge, icon |
| Low | `#6B7280` | Left border, badge, icon |

**Status colors:**

| State | Hex |
|---|---|
| Healthy/OK | `#22C55E` |
| Warning | `#F59E0B` |
| Error/Down | `#EF4444` |

Rule: severity colors are exclusively reserved for threat severity. Status colors are exclusively reserved for system/pipeline health. Never mix the two systems, or analysts will misread a healthy pipeline indicator as a threat signal or vice versa.

### 3.3 Typography

| Role | Font | Size | Weight |
|---|---|---|---|
| App title | Inter or system-ui | 20px | 600 |
| Section headers | Inter | 14px | 600, uppercase, letter-spaced |
| Body/alert text | Inter | 13-14px | 400 |
| Metadata/timestamps | JetBrains Mono or Roboto Mono | 12px | 400 |
| Data/evidence values | JetBrains Mono | 13px | 500 |

Monospace font specifically for IPs, ports, hashes, and feature values — these are scanned/compared numerically by analysts and monospace alignment materially speeds recognition.

### 3.4 Iconography

Use a single consistent icon set (Lucide or Feather — outline style, not filled) throughout. Reserve filled/solid icon variants exclusively for active/selected states, so fill itself carries meaning.

### 3.5 Spacing & Layout Grid

- Base unit: 4px
- Card padding: 12-16px
- Section gaps: 24px
- Sidebar width: 240px (collapsible to 64px icon-only)
- Max content width: none — dashboard is designed for wide/ultra-wide SOC monitors, uses full viewport width with responsive column reflow

---

## 4. Information Architecture

```
App Shell
├── Sidebar (persistent navigation)
│   ├── Live Feed (default view)
│   ├── Historical Search
│   ├── Incidents
│   ├── Health & Pipeline
│   └── Admin (role-gated)
├── Top Bar
│   ├── Global severity summary (counts: critical/high/medium/low)
│   ├── Connection status indicator (live/reconnecting/down)
│   └── User/role indicator
└── Main Content Area (view-dependent)
```

---

## 5. Screen Specifications

### 5.1 Live Feed (primary/default view)

**Layout:** Two-column. Left = alert stream (65% width). Right = evidence detail panel (35% width, persistent, updates on selection).

**Alert row/card:**
```
┌─────────────────────────────────────────────────┐
│ ▍ DDOS · CRITICAL              conf 94%   2s ago │
│ ▍ 10.0.0.10 ← 185.10.20.30                       │
│ ▍ SYN flood, entropy spike, 8.2k pps              │
└─────────────────────────────────────────────────┘
```
- Left border (4px): severity color — the single fastest scan cue
- Threat class badge, top-left
- Confidence percentage, top-right
- Relative timestamp, top-right (auto-updating, e.g., "2s ago" → "1m ago")
- Flow summary line (src ← dst) in monospace
- One-line evidence summary auto-generated from top triggered feature
- New alerts animate in at the top with a brief highlight flash (300ms fade), never a jarring pop or sound by default (configurable)
- Clicking a row selects it, populating the detail panel; selected row gets a persistent left-accent highlight

**Filter bar (above the feed):**
- Threat class multi-select chips
- Severity multi-select chips
- Sensor dropdown (for multi-sensor deployments)
- Search box (free text against flow_id/evidence)
- Clear-all control, always visible when any filter is active

**Evidence detail panel:**
- Full alert metadata (alert_id, timestamp, sensor, flow identifier)
- Evidence table: feature name / value / baseline comparison, monospace values
- Model attribution (which detector/model produced this)
- Related alerts list (clickable, jumps to that alert)
- Status control (new / acknowledged / investigating / resolved / false positive) — dropdown, persists via API call

### 5.2 Historical Search

**Layout:** Filter bar (same as Live Feed) + date/time range picker + results table (not cards — table is denser and more appropriate for scanning past data).

**Table columns:** Timestamp, Threat Class, Severity, Confidence, Source, Destination, Status.

Row click opens the same evidence detail panel as Live Feed, as a slide-over drawer rather than a fixed column (since this view prioritizes table density).

### 5.3 Incidents (correlation view)

**Layout:** Card-per-incident, each card expandable to reveal its constituent alerts.

```
┌───────────────────────────────────────────────────┐
│ ⬤ Incident — 172.16.2.31          3 signals · HIGH │
│   recon → c2_beacon → tls_malware                   │
│   First seen 09:41   Last seen 09:58                │
└───────────────────────────────────────────────────┘
```
- Grouped by source host exhibiting multiple threat signals within a time window
- Timeline mini-visualization showing the sequence of signals (attack progression story)
- Expand reveals individual alerts, reusing the Alert Card component from Live Feed

### 5.4 Health & Pipeline

**Layout:** Grid of metric cards + charts, engineering-oriented rather than analyst-oriented.

- Throughput chart (flows/sec, time series)
- End-to-end latency chart (p50/p95/p99 lines)
- Kafka consumer lag per topic (bar or gauge)
- Per-sensor status list (green/amber/red dot + last-seen timestamp)
- Per-detector status (running/error, alerts/min)
- "No return path" architecture confirmation panel — a static/verified badge state confirming network isolation, reinforcing the platform's core guarantee visually

### 5.5 Admin (role-gated)

- Per-detector threshold configuration forms (sliders/numeric inputs with current value + description of effect)
- Threat-intel feed status (JA3 blocklist last updated, DGA corpus last updated) with manual refresh trigger
- User/role management table (if multi-user in scope)

---

## 6. Component Library (buildable inventory)

| Component | States |
|---|---|
| `AlertCard` | default, selected, new (animating in), hovered |
| `SeverityBadge` | critical, high, medium, low |
| `ConfidenceMeter` | numeric + small radial or bar indicator |
| `EvidenceTable` | populated, empty |
| `FilterChip` | active, inactive |
| `StatusDot` | healthy, warning, error, unknown |
| `ConnectionIndicator` | live, reconnecting, disconnected |
| `IncidentCard` | collapsed, expanded |
| `MetricChart` | loading, populated, no-data |
| `ThresholdSlider` | default, dirty (unsaved change), saved |
| `Toast/InlineNotice` | info, warning, error — used sparingly, never for routine alert arrival (that's the live feed's job) |

Build each as an isolated, reusable component (Storybook or equivalent recommended) before wiring into full screens — this keeps severity/status color usage consistent by construction rather than by convention.

---

## 7. Interaction & Motion Guidelines

- New alert arrival: 300ms fade/slide-in at top of feed, no sound by default, no layout jump for already-visible rows
- Selection: instant (no transition delay) — analysts need immediate response when triaging under alert volume
- Chart updates: smooth transition (~500ms) rather than instant redraw, to avoid visual flicker on frequently-updating health metrics
- Loading states: skeleton placeholders matching final content shape, never blank white/dark flashes
- Connection loss: persistent, unmissable banner (not a toast that disappears) until reconnected — silent disconnection is a critical trust failure for a live-monitoring tool

---

## 8. Accessibility & Usability

- Minimum contrast ratio 4.5:1 for all text against background (verify severity colors against `bg-surface` specifically, as these are the most safety-critical text/background pairs)
- Severity must never be conveyed by color alone — always paired with text label and/or icon, for colorblind accessibility
- All interactive elements keyboard-navigable (critical for power-user analysts who avoid mouse-only workflows)
- Live regions (ARIA) for the alert feed so screen readers announce new critical alerts

---

## 9. Responsive Behavior

Primary target: large desktop/wall-monitor displays (1920px+), as this is SOC operational tooling, not a mobile-first product. Secondary target: standard laptop displays (1366-1440px) — sidebar collapses to icon-only, evidence panel becomes a slide-over drawer instead of a persistent column below ~1600px width. No dedicated mobile layout required for v1.

---

## 10. Design-to-Engineering Handoff Notes

- All colors/spacing/typography values above should be implemented as CSS custom properties (design tokens), not hardcoded per-component, so theme adjustments propagate globally
- Severity and status color systems should be exposed as shared constants imported wherever needed — never redefined locally in a component
- Component states listed in §6 should each have a corresponding Storybook story (or equivalent) before integration, to catch inconsistent state handling early