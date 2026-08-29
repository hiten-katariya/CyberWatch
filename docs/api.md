# API Specification & Data Model Document
## Passive One-Way Network Threat Detection & Intelligence Platform

**Version:** 1.0 · **Companion to:** PRD v1.0, Technical Design Document v1.0

---

## Part A: API Specification

### A.1 Overview

- **Base URL:** `https://api.threatpipe.internal/v1`
- **Protocols:** REST (JSON over HTTPS) for queries/config, WebSocket (WSS) for live alert streaming
- **Auth:** OAuth2/OIDC bearer tokens (`Authorization: Bearer <token>`) on every request
- **Content type:** `application/json` for all request/response bodies unless noted
- **Versioning:** URL-path versioned (`/v1/...`); breaking changes require a new version path, additive changes (new optional fields) do not

### A.2 Roles & Permissions

| Role | Access |
|---|---|
| `analyst` | Read-only: alerts, incidents, health, historical search |
| `engineer` | `analyst` scope + read on detector config/thresholds |
| `admin` | Full access: config writes, threat-intel refresh triggers, user management |

Every endpoint below specifies its minimum required role.

---

### A.3 REST Endpoints

#### `GET /alerts`
**Role:** `analyst`
List alerts with filtering and pagination.

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `threat_class` | string (repeatable) | No | Filter by one or more threat classes |
| `severity` | string (repeatable) | No | Filter by severity |
| `src_ip` | string | No | Filter by source IP |
| `dst_ip` | string | No | Filter by destination IP |
| `sensor_id` | string | No | Filter by sensor |
| `status` | string | No | Filter by alert status |
| `from` | ISO8601 | No | Start of time range |
| `to` | ISO8601 | No | End of time range |
| `limit` | int | No | Default 50, max 500 |
| `cursor` | string | No | Pagination cursor from previous response |

**Response `200`:**
```json
{
  "items": [ { "...": "AlertObject, see A.6" } ],
  "next_cursor": "string|null",
  "total_matched": 1342
}
```

---

#### `GET /alerts/{alert_id}`
**Role:** `analyst`
Full detail for a single alert, including evidence.

**Response `200`:** `AlertObject` (see A.6)
**Response `404`:** alert not found

---

#### `PATCH /alerts/{alert_id}`
**Role:** `analyst`
Update alert status (analyst triage action).

**Request body:**
```json
{ "status": "acknowledged | investigating | resolved | false_positive" }
```
**Response `200`:** updated `AlertObject`
**Response `400`:** invalid status transition (see A.7 for allowed transitions)

---

#### `GET /incidents`
**Role:** `analyst`
List correlated alert groupings.

**Query parameters:** `src_ip`, `from`, `to`, `severity`, `limit`, `cursor` (same semantics as `/alerts`)

**Response `200`:**
```json
{
  "items": [
    {
      "incident_id": "uuid",
      "primary_host": "string",
      "severity": "string",
      "first_seen": "ISO8601",
      "last_seen": "ISO8601",
      "threat_classes": ["recon", "c2_beacon", "encrypted_malware"],
      "alert_ids": ["uuid", "..."]
    }
  ],
  "next_cursor": "string|null"
}
```

---

#### `GET /incidents/{incident_id}`
**Role:** `analyst`
Full incident detail with embedded alert objects.

**Response `200`:**
```json
{
  "incident_id": "uuid",
  "primary_host": "string",
  "severity": "string",
  "first_seen": "ISO8601",
  "last_seen": "ISO8601",
  "alerts": [ { "...": "AlertObject" } ]
}
```

---

#### `GET /health`
**Role:** `analyst`
Aggregated pipeline health snapshot.

**Response `200`:**
```json
{
  "timestamp": "ISO8601",
  "throughput_flows_per_sec": 512.4,
  "latency_ms": { "p50": 3200, "p95": 8900, "p99": 14200 },
  "kafka_lag": { "events.conn": 12, "features.conn": 3, "alerts": 0 },
  "sensors": [
    { "sensor_id": "sim-sensor-01", "status": "healthy", "last_seen": "ISO8601" }
  ],
  "detectors": [
    { "name": "detector-ddos", "status": "running", "alerts_per_min": 1.2 }
  ]
}
```

---

#### `GET /config/detectors`
**Role:** `engineer`
Current detector configuration/thresholds.

**Response `200`:**
```json
{
  "detectors": [
    {
      "name": "detector-ddos",
      "enabled": true,
      "thresholds": { "syn_rate_multiplier": 5.0, "entropy_min": 0.85 },
      "cooldown_sec": 300
    }
  ]
}
```

---

#### `PUT /config/detectors/{detector_name}`
**Role:** `admin`
Update thresholds/config for a specific detector.

**Request body:**
```json
{
  "enabled": true,
  "thresholds": { "syn_rate_multiplier": 4.5 },
  "cooldown_sec": 300
}
```
**Response `200`:** updated config object
**Response `403`:** insufficient role
**Response `422`:** invalid threshold value (out of allowed range)

All config changes are appended to an audit log (see A.8) automatically — not a separate call the client needs to make.

---

#### `GET /threat-intel/status`
**Role:** `engineer`
Status of threat-intelligence feeds.

**Response `200`:**
```json
{
  "feeds": [
    { "name": "ja3_blocklist", "last_updated": "ISO8601", "record_count": 4210 },
    { "name": "dga_corpus", "last_updated": "ISO8601", "record_count": 89000 }
  ]
}
```

---

#### `POST /threat-intel/refresh`
**Role:** `admin`
Manually trigger a threat-intel feed refresh (out-of-band from the ingest network, per architectural constraint).

**Response `202`:** `{ "job_id": "uuid", "status": "queued" }`

---

#### `GET /audit-log`
**Role:** `admin`
Config change history.

**Response `200`:**
```json
{
  "items": [
    { "timestamp": "ISO8601", "actor": "user@org.com", "action": "update_config",
      "target": "detector-ddos", "before": {}, "after": {} }
  ]
}
```

---

### A.4 WebSocket: `WSS /ws/alerts`

**Role:** `analyst`
**Auth:** token passed as query param or subprotocol header at connect time (`?token=...`)

**Server → client messages:**

```json
{ "type": "alert", "data": { "...": "AlertObject" } }
```
```json
{ "type": "heartbeat", "timestamp": "ISO8601" }
```
```json
{ "type": "connection_status", "status": "live" }
```

**Client → server messages (optional, for server-side filtering to reduce bandwidth):**
```json
{ "type": "subscribe", "filters": { "threat_class": ["ddos", "c2_beacon"] } }
```

**Reconnection behavior:** Client must implement exponential backoff; on reconnect, client should call `GET /alerts?from=<last_known_timestamp>` to backfill any alerts missed during the disconnect window before resuming live stream.

---

### A.5 Error Response Format (standard across all endpoints)

```json
{
  "error": {
    "code": "string (machine-readable, e.g. INVALID_STATUS_TRANSITION)",
    "message": "string (human-readable)",
    "details": {}
  }
}
```

| HTTP Status | Meaning |
|---|---|
| 400 | Malformed request |
| 401 | Missing/invalid auth token |
| 403 | Authenticated but insufficient role |
| 404 | Resource not found |
| 422 | Valid request shape, semantically invalid value |
| 429 | Rate limited |
| 500 | Internal error |

---

### A.6 `AlertObject` (canonical, referenced above)

```json
{
  "schema_version": "1.0",
  "alert_id": "uuid",
  "timestamp": "ISO8601",
  "sensor_id": "string",
  "threat_class": "ddos | c2_beacon | dga | dns_tunnel | encrypted_malware | recon | exfiltration",
  "severity": "low | medium | high | critical",
  "confidence": 0.0,
  "flow_identifier": {
    "src_ip": "string", "dst_ip": "string",
    "src_port": "int|null", "dst_port": "int|null",
    "proto": "tcp|udp",
    "scope_type": "flow | host-pair | host",
    "observation_window": ["start_ms", "end_ms"]
  },
  "evidence": [
    { "feature": "string", "value": "number|string", "verdict": "string", "baseline_range": "string|null" }
  ],
  "related_alerts": ["uuid"],
  "status": "new | acknowledged | investigating | resolved | false_positive"
}
```

### A.7 Alert Status State Machine

```
new ──► acknowledged ──► investigating ──► resolved
  │                            │
  └──────────► false_positive ◄┘
```
Allowed transitions only as shown above; `PATCH /alerts/{id}` rejects any transition not on this diagram with `400 INVALID_STATUS_TRANSITION`. `resolved` and `false_positive` are terminal — no further transitions permitted from either.

### A.8 Rate Limiting

- REST: 300 requests/min per token (analyst/engineer), 600/min (admin)
- WebSocket: 1 connection per token enforced; server sends `connection_status: replaced` and closes the old connection if a second connect occurs with the same token

---

## Part B: Data Model

### B.1 Entity Relationship Overview

```
sensors ──1:N──► alerts ──N:1──► incidents
                    │
                    └──N:1──► detector_configs (via threat_class)

users ──1:N──► audit_log
threat_intel_feeds (standalone, referenced by name in detector logic)
```

### B.2 Table: `alerts`

Primary operational table. Hypertable partitioned on `ts` (TimescaleDB).

```sql
CREATE TABLE alerts (
    alert_id        UUID PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL,
    sensor_id       TEXT NOT NULL,
    threat_class    TEXT NOT NULL,
    severity        TEXT NOT NULL,
    confidence      REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    src_ip          INET,
    dst_ip          INET,
    src_port        INT,
    dst_port        INT,
    proto           TEXT,
    scope_type      TEXT,
    window_start_ms BIGINT,
    window_end_ms   BIGINT,
    evidence        JSONB NOT NULL,
    incident_id     UUID,
    status          TEXT NOT NULL DEFAULT 'new',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('alerts', 'ts');
CREATE INDEX idx_alerts_class_ts   ON alerts (threat_class, ts DESC);
CREATE INDEX idx_alerts_src_ts     ON alerts (src_ip, ts DESC);
CREATE INDEX idx_alerts_incident   ON alerts (incident_id);
CREATE INDEX idx_alerts_status     ON alerts (status) WHERE status != 'resolved';
```

**Notes:**
- `evidence` stored as JSONB (matches the `AlertObject.evidence` array) — queryable via Postgres JSONB operators for ad-hoc analysis without a schema migration per new feature type
- `incident_id` nullable — populated asynchronously by the correlation job, not at alert-insert time

---

### B.3 Table: `incidents`

```sql
CREATE TABLE incidents (
    incident_id     UUID PRIMARY KEY,
    primary_host    INET NOT NULL,
    severity        TEXT NOT NULL,
    first_seen      TIMESTAMPTZ NOT NULL,
    last_seen       TIMESTAMPTZ NOT NULL,
    threat_classes  TEXT[] NOT NULL,
    alert_count     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_incidents_host ON incidents (primary_host, last_seen DESC);
```

Populated/updated by an async correlation worker that groups alerts by `src_ip` within a rolling time window (e.g., 30 min) — not written directly by detectors.

---

### B.4 Table: `sensors`

```sql
CREATE TABLE sensors (
    sensor_id       TEXT PRIMARY KEY,
    display_name    TEXT,
    location        TEXT,
    status          TEXT NOT NULL DEFAULT 'unknown',
    last_seen       TIMESTAMPTZ,
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Used by `/health` to report per-sensor status; a sensor row's `last_seen` is updated by a heartbeat mechanism from the ingest adapter, not from alert traffic (so a quiet-but-healthy sensor doesn't appear stale).

---

### B.5 Table: `detector_configs`

```sql
CREATE TABLE detector_configs (
    detector_name   TEXT PRIMARY KEY,
    enabled         BOOLEAN NOT NULL DEFAULT true,
    thresholds      JSONB NOT NULL,
    cooldown_sec    INT NOT NULL DEFAULT 300,
    updated_by      TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`thresholds` JSONB shape is detector-specific (e.g., `{"syn_rate_multiplier": 5.0, "entropy_min": 0.85}` for DDoS) — validated at the application layer against a per-detector JSON schema before write, since Postgres can't enforce detector-specific shape constraints natively.

---

Part B.6 threat_intel_feeds — updated schema
sql
CREATE TABLE threat_intel_feeds (
    feed_name       TEXT PRIMARY KEY,
    source_url      TEXT,
    access_tier     TEXT,          -- NEW: e.g. 'public', 'research-request', 'commercial'
    license_note    TEXT,          -- NEW: attribution/usage restriction summary
    last_updated    TIMESTAMPTZ,
    record_count    INT,
    status          TEXT DEFAULT 'ok'
);

Rationale: DGArchive access is typically gated behind a research request rather than fully open, so tracking access tier and license terms here prevents accidental misuse or redistribution of restricted data, and makes it auditable alongside the rest of the config/feed metadata.
---

### B.7 Table: `users`

```sql
CREATE TABLE users (
    user_id         UUID PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('analyst','engineer','admin')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Minimal — assumes OIDC provider handles credential/identity management; this table only maps identity to role.

---

### B.8 Table: `audit_log`

```sql
CREATE TABLE audit_log (
    log_id          UUID PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    target          TEXT,
    before_state    JSONB,
    after_state     JSONB
);

CREATE INDEX idx_audit_ts ON audit_log (ts DESC);
```

Written automatically on every `PUT /config/detectors/*` and `POST /threat-intel/refresh` call — never written to directly by any other path.

---

### B.9 Retention Policy

| Table | Hot retention | Archival |
|---|---|---|
| `alerts` | 90 days (configurable) | Exported to cold/object storage beyond hot window via TimescaleDB continuous aggregate + retention policy |
| `incidents` | 90 days | Archived alongside constituent alerts |
| `audit_log` | Indefinite (compliance) | N/A |
| `sensors`, `detector_configs`, `threat_intel_feeds` | Indefinite (current-state tables) | N/A |

---

## Part C: Schema-Contract Consistency Note

The `AlertObject` in Part A.6 and the `alerts` table in Part B.2 must remain field-for-field consistent. Any addition of a new evidence field or top-level attribute requires updating both this document and the `schema_version` value in the alert payload — treat `schema_version` bumps as a coordination point between backend and frontend, not an internal implementation detail.