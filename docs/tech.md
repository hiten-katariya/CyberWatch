# Technical Design Document (TDD)
## Passive One-Way Network Threat Detection & Intelligence Platform

**Version:** 1.1 · **Companion to:** PRD v1.1

---

## 1. Purpose & Scope

This document specifies the technical implementation of the system described in the PRD: component-level design, data flow, schemas, APIs, storage models, ML pipeline design, deployment topology, lab/test environment, and operational concerns. It is the reference for engineering implementation.

---

## 2. High-Level Architecture

```
┌─────────────┐   one-way    ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐
│ Mirrored/    │──diode/SPAN─►│ Sensor Layer │───►│ Streaming Bus│───►│ Feature Extraction │
│ Diode Feed   │              │ (Zeek)       │    │ (Kafka)      │    │ Service (stateful) │
└─────────────┘              └──────────────┘    └──────────────┘    └─────────┬──────────┘
      ▲                                                                        │
      │ (lab only, isolated)                                                  ▼
┌─────────────┐    ┌───────────────┐    ┌──────────────┐    ┌────────────────────┐
│ Analyst      │◄───│ API Layer     │◄───│ Alert Store  │◄───│ Detection Services  │
│ Dashboard    │    │ (REST + WS)   │    │ (TimescaleDB)│    │ (per threat class)  │
└─────────────┘    └───────────────┘    └──────────────┘    └────────────────────┘
```

Every arrow above is one-directional in the request sense; no service downstream of the Sensor Layer ever opens an outbound connection back toward the mirrored feed, monitored hosts, or the diode boundary. The traffic-generation environment used during development (see §4) feeds into the same one-way mirror point, preserving architectural parity between lab testing and production deployment.

---

## 3. Component Specifications

### 3.1 Sensor Layer

**Responsibility:** Convert raw packet data into structured protocol records.

- **Technology:** Zeek (network security monitor), deployed as a dedicated process per ingest interface.
- **Inputs:** Live capture interface (AF_PACKET) or replicated/mirrored feed — in development, this is the mirror/SPAN output of the isolated lab network (§4).
- **Outputs:** Structured logs — `conn.log` (flow records), `dns.log` (DNS queries/responses), `ssl.log`/`x509.log` (TLS handshake metadata including JA3/JA3S).
- **Key config:** JA3 fingerprinting plugin enabled; log rotation interval tuned to balance latency vs. file-handle overhead (recommend 1-5s rotation for near-real-time forwarding, or direct Zeek→Kafka plugin instead of file rotation where available).
- **Scaling:** One Zeek instance per sensor/ingest point; each tagged with a unique `sensor_id` propagated through all downstream records.
- **Failure mode:** If Zeek crashes, ingest for that sensor pauses (fails closed — no data loss risk to the rest of the pipeline, but that sensor's coverage gap must be visible in the health dashboard).

### 3.2 Ingest Adapter

**Responsibility:** Tail Zeek log output (or consume Zeek's native Kafka plugin output) and publish normalized JSON records onto Kafka topics.

- **Technology:** Lightweight Python/Go service.
- **Behavior:** Parses Zeek's TSV log format, converts to JSON, attaches `sensor_id` and ingest timestamp, publishes to per-record-type topics.
- **Topics produced:** `events.conn`, `events.dns`, `events.tls`
- **Delivery guarantee:** At-least-once (Kafka producer with acks=all); downstream consumers must be idempotent (dedupe on natural keys + timestamp).

### 3.3 Streaming Bus

**Responsibility:** Durable, replayable, partitioned message backbone decoupling ingest from processing.

- **Technology:** Apache Kafka (KRaft mode, no ZooKeeper dependency).
- **Topic design:**

| Topic | Partition key | Retention | Purpose |
|---|---|---|---|
| `events.conn` | `src_ip` | 24h (configurable) | Raw flow records |
| `events.dns` | `src_ip` | 24h | Raw DNS records |
| `events.tls` | `src_ip` | 24h | Raw TLS handshake records |
| `features.*` | flow/host key | 6h | Computed windowed features per detector domain |
| `alerts` | `alert_id` | 30d+ (or long-term via sink) | Final structured alerts |

- **Partitioning rationale:** Partitioning by `src_ip` (or composite flow key where needed) preserves per-key ordering, which is required for correct stateful windowing downstream, while enabling horizontal scale-out of consumers.
- **Scaling:** Partition count set based on target throughput; consumer groups scale independently per service.

### 3.4 Feature Extraction Service

**Responsibility:** Maintain windowed, stateful statistics per key needed by detectors.

- **Technology:** Python asyncio consumers (or Kafka Streams/Flink if team has JVM stream-processing experience and higher throughput is required).
- **State model:** In-memory per-key state dictionaries, checkpointed periodically (or backed by RocksDB-style local state store for crash recovery in a scaled deployment).
- **Windowing:**
  - Tumbling 60s windows for DDoS/scan-oriented features
  - Sliding 10-minute windows, 30s hop, for beaconing/exfiltration features
  - Event-time watermarking: watermark = max observed timestamp − 10s; windows only close once the watermark passes them, guaranteeing deterministic results regardless of ingest speed or replay
- **State hygiene:** LRU eviction of keys idle > 30 minutes; HyperLogLog used for cardinality-heavy features (distinct destination counts) to bound memory.
- **Output:** Publishes computed feature vectors to `features.*` topics, keyed identically to input for consumer affinity.

### 3.5 Detection Services

**Responsibility:** Consume feature streams, apply detection logic, emit alerts.

- **Deployment model:** One independently deployable service per threat class (six total), each consuming only the feature topic(s) relevant to it. This isolates failure/scaling per class and allows independent tuning/redeployment.

| Service | Consumes | Core logic | Sub-pattern differentiation |
|---|---|---|---|
| `detector-ddos` | `features.conn` | EWMA baseline deviation + source-IP entropy + IsolationForest | Distinguishes `volumetric_syn`, `volumetric_udp`, and `slow_exhaustion` patterns based on pps/duration/connection-hold-time profile |
| `detector-recon` | `features.conn` | HyperLogLog fan-out cardinality vs. threshold | — |
| `detector-c2` | `features.conn` | Inter-arrival coefficient of variation, autocorrelation | — |
| `detector-dga` | `features.dns` | Trained classifier (LightGBM) on lexical features + separate tunnelling rule path | Splits logic internally: `dga` (domain-generation) vs `dns_tunnel` (query-length/type anomaly) |
| `detector-tls` | `features.tls` | JA3/JA3S/JA4 blocklist match + fingerprint-rarity anomaly | — |
| `detector-exfil` | `features.conn` | Byte-ratio z-score vs. per-host baseline | — |

- **Scoring pattern:** Each detector computes a raw score, applies a calibration function (isotonic/Platt scaling fit during training) to produce a bounded, meaningful `confidence` value — never a raw, uncalibrated logit surfaced to the analyst.
- **Deduplication:** Alert key = hash(source, threat_class); a cooldown window (default 5 min, configurable) suppresses repeat alerts for the same ongoing condition, while updating an internal "still active" counter rather than spamming new alert rows.
- **Output:** Publishes structured alert JSON (see §6) to the `alerts` topic, including an `evidence.pattern` field where sub-classification applies (DDoS, DGA/tunnel).

### 3.6 Threat-Intelligence Feed Manager

**Responsibility:** Keep JA3 blocklists and DGA training corpora current.

- **Technology:** Scheduled job (cron-style) running on a network segment isolated from the monitoring enclave's ingest path.
- **Sources:** Public JA3/JA4 blocklists (e.g., abuse.ch SSLBL), DGArchive family-labeled domain samples, Tranco top-1M as benign-domain contrast.
- **Access management:** DGArchive access is typically gated behind a research request rather than fully open. Access tier obtained and any license/usage restrictions are recorded in the `threat_intel_feeds` metadata table (§7.6) and must be respected — no redistribution of raw domain lists outside the project.
- **Delivery:** Pushes updated artifacts to a shared model/config store consumed by detection services on a hot-reload cycle (no full pipeline restart required).
- **Isolation constraint:** This service's outbound internet access must be on a network path entirely separate from the diode/mirror ingest network, to avoid any ambiguity about the one-way guarantee.

### 3.7 Alert Store

**Responsibility:** Durable, queryable persistence of alerts.

- **Technology:** TimescaleDB (Postgres + time-series extension).
- **Schema:** See §7. Hypertable partitioned on `timestamp` for efficient time-range queries.
- **Sink mechanism:** A dedicated Kafka consumer (`alert-sink`) reads from the `alerts` topic and performs idempotent upserts (`ON CONFLICT DO NOTHING`/`UPDATE` on `alert_id`).
- **Retention:** Configurable hot-storage window (e.g., 90 days) with optional archival export (cold storage/object store) beyond that.

### 3.8 API Layer

**Responsibility:** Serve alert data and live updates to the frontend; expose admin/config endpoints.

- **Technology:** FastAPI (REST + WebSocket support natively).
- **Endpoints:** See standalone API Specification document for full contract (REST endpoints, WebSocket message format, auth, error schema).
- **Auth:** OAuth2/OIDC bearer tokens; role-based access (`analyst` read-only on alerts, `engineer` read on config, `admin` for config writes and threat-intel refresh).

### 3.9 Frontend Dashboard

**Responsibility:** Analyst-facing UI for live monitoring, triage, and investigation.

- **Technology:** React (Vite build), WebSocket client for live feed, REST client for historical/admin queries.
- **State management:** Zustand (lightweight, avoids Redux boilerplate) holding: live alert list, active filters, selected alert, health metrics.
- **Component breakdown:**
  - `LiveFeed` — subscribes to `/ws/alerts`, prepends new alerts, capped list length with virtualized scroll for performance
  - `AlertCard` — severity-coded summary row
  - `EvidenceDrawer` — expands full evidence JSON into readable feature/value pairs, including `pattern` field when present
  - `FilterBar` — threat class, severity, time range, sensor
  - `IncidentView` — groups alerts by `related_alerts`
  - `HealthPanel` — polls `/health` every 5-10s, renders throughput/latency/lag charts
  - `AdminPanel` — threshold config forms, gated by role

---

## 4. Traffic Generation & Lab Environment

### 4.1 Purpose

Detection logic is developed and validated against a combination of realistic synthetic traffic and real, industry-standard network tools, to ensure detectors generalize to genuine attacker behavior rather than idealized synthetic patterns.

### 4.2 Network Isolation

- All traffic generation occurs within a dedicated, isolated network namespace (`lab-net` — Docker network or VLAN) with no route to production, corporate, or public-internet-reachable infrastructure.
- The mirror/SPAN mechanism from `lab-net`'s gateway feeds the Zeek sensor identically to how a production diode/mirror would — preserving architectural parity.
- No component in `lab-net` has outbound internet access, except the isolated threat-intel update path (§3.6), which is physically/logically separate.

### 4.3 Tooling

| Tool | Category | Threat class(es) exercised |
|---|---|---|
| iperf3 | Benign traffic | Baseline for all detectors |
| Ostinato / TRex | Benign traffic, load testing | Baseline + throughput/load testing |
| hping3 | Attack tool | DDoS (SYN flood, UDP flood) |
| Slowloris | Attack tool | DDoS (slow connection exhaustion) |
| dnscat2 | Attack tool | DNS tunnelling |
| iodine | Attack tool | DNS tunnelling (alternate) |
| DGArchive samples | Labeled dataset | DGA domain detection |
| Sandboxed C2 emulator | Attack tool | C2 beaconing |
| Scapy | Custom synthetic traffic | Recon/port scan, exfiltration (no dedicated real-tool equivalent used) |

### 4.4 Ground Truth Capture

Since real tools do not self-report attack timing the way a custom script does, every tool invocation is wrapped to capture start/end timestamps, appended to a manifest file:

```json
{"tool": "hping3", "type": "syn_flood", "start_ts": 1735300000, "end_ts": 1735300030, "src": "185.10.20.30", "dst": "10.0.0.10"}
```

This manifest is the ground truth input to the evaluation harness (§10). Because real-tool timestamps are coarser than a scripted scenario's, the evaluation harness uses a wider matching tolerance (±2s) than exact timestamp alignment.

### 4.5 Safety Requirements

- Attack tools (hping3, Slowloris, dnscat2, iodine) are installed and run only inside `lab-net` containers/VMs, never on host machines with broader network access.
- Isolation is verified (via network inspection/routing table check) before any attack tool is run for the first time.
- Full tool inventory, versions, and verification checklist maintained in `docs/lab-environment.md`.

---

## 5. Data Flow (Detailed)

```
1. Packet arrives at mirror port / diode output (production or lab-net)
2. Zeek parses → conn.log / dns.log / ssl.log entries written
3. Ingest adapter tails logs → JSON → Kafka (events.* topics)
4. Feature extraction service consumes events.* → maintains windowed state
   → on window close, publishes computed features to features.* topics
5. Detection services consume features.* → apply rule/ML logic
   → on threshold breach, construct alert (with sub-pattern where applicable) → publish to alerts topic
6. Alert-sink consumer writes alert to TimescaleDB
7. API layer's WebSocket handler (separate consumer on alerts topic)
   pushes alert to all connected dashboard clients in real time
8. Dashboard renders alert; analyst can also query historical alerts via REST
```

Latency budget per stage (target, p95):
- Zeek parse: ~1s
- Kafka transit: <100ms
- Feature window evaluation: ≤10s (bounded by window/watermark config)
- Detection + alert publish: <500ms
- **Total: ≤15s packet-to-dashboard**

---

## 6. Data Schemas

### 6.1 Alert schema (canonical)

```json
{
  "schema_version": "1.0",
  "alert_id": "uuid4",
  "timestamp": "ISO8601",
  "sensor_id": "string",
  "threat_class": "ddos | c2_beacon | dga | dns_tunnel | encrypted_malware | recon | exfiltration",
  "severity": "low | medium | high | critical",
  "confidence": "float 0.0-1.0",
  "flow_identifier": {
    "src_ip": "string",
    "dst_ip": "string",
    "src_port": "int|null",
    "dst_port": "int|null",
    "proto": "tcp|udp",
    "scope_type": "flow | host-pair | host",
    "observation_window": ["start_ms", "end_ms"]
  },
  "evidence": [
    {"feature": "string", "value": "number|string", "verdict": "string", "baseline_range": "string|null"}
  ],
  "related_alerts": ["alert_id"],
  "status": "new | acknowledged | investigating | resolved | false_positive"
}
```

Note: sub-pattern classification (e.g., `volumetric_syn` vs `slow_exhaustion` for DDoS) is carried as a named entry within the `evidence` array (`{"feature": "pattern", "value": "slow_exhaustion", ...}`) rather than a top-level field, keeping the schema stable across all threat classes.

### 6.2 TimescaleDB table (alerts)

```sql
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    sensor_id TEXT,
    threat_class TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL NOT NULL,
    src_ip INET,
    dst_ip INET,
    src_port INT,
    dst_port INT,
    proto TEXT,
    evidence JSONB,
    related_alerts UUID[],
    status TEXT DEFAULT 'new'
);
SELECT create_hypertable('alerts', 'ts');
CREATE INDEX idx_alerts_class ON alerts (threat_class, ts DESC);
CREATE INDEX idx_alerts_src ON alerts (src_ip, ts DESC);
```

---

## 7. ML Model Design

| Detector | Model type | Training data | Validation approach |
|---|---|---|---|
| DGA | LightGBM (gradient-boosted trees) on lexical features (entropy, n-gram frequency, length, digit ratio) | **DGArchive family-labeled domain samples** + Tranco top-1M as benign class | Leave-one-DGA-family-out cross-validation against real malware families (tests generalization, not memorization) |
| Anomaly layer (DDoS/scan/exfil) | IsolationForest, per-feature-set | Benign-traffic baseline from iperf3/Ostinato/TRex captures | Contamination-rate tuned against false-positive budget on held-out benign traffic |
| TLS fingerprint | Exact-match lookup (not ML) + IsolationForest on fingerprint-rarity/timing features | Threat-intel JA3 blocklist + observed fingerprint frequency table | Precision tracked on known-bad fingerprint hit rate |
| C2 beacon | Statistical (non-ML): CV/autocorrelation scoring | Sandboxed C2 emulator output at varying interval/jitter configurations | Validated against emulator ground truth across jitter levels |
| DDoS sub-pattern classification | Rule-based split within `detector-ddos` (not a separate ML model) | hping3 (SYN/UDP flood profiles), Slowloris (connection-hold-time profile) | Manual verification each sub-pattern maps to correct `pattern` evidence value |

**Confidence calibration:** All raw model scores pass through an isotonic or Platt-scaling calibration step fit on a held-out set, so a confidence of 0.9 means something consistent across detectors rather than being an arbitrary uncalibrated number.

**Retraining cadence:** DGA and anomaly-baseline models retrained on a scheduled cadence (e.g., weekly) using recent benign traffic and refreshed DGArchive data to account for drift; retraining pipeline is a separate offline job, not part of the real-time path.

**Data access note:** DGArchive access tier (public sample vs. research-request full access) determines the size/diversity of training data available; whichever tier is obtained is documented in `docs/models.md` and tracked in the `threat_intel_feeds` table's `access_tier`/`license_note` fields.

---

## 8. Deployment Architecture

- **Containerization:** Every component is a separate Docker image; orchestrated via Kubernetes for production, Docker Compose acceptable for smaller/single-node deployments.
- **Network segmentation:**
  - Monitoring enclave network: sensor, Kafka, feature extraction, detection services, alert store — no egress route to production/monitored network
  - Separate "intel update" network: threat-intel feed manager only, with controlled internet egress, physically/logically isolated from the ingest network
  - Analyst-facing network: API + dashboard, reachable by SOC analysts, reads only from the alert store (no path back into the monitoring enclave's ingest side)
  - Lab/test network (`lab-net`): development and validation only, isolated from all of the above except via the one-way mirror into the Zeek sensor — never present in a production deployment
- **Scaling levers:**
  - Kafka partition count (throughput)
  - Detection service replica count per class (independent scaling based on which threat class sees the most load)
  - Feature extraction consumer group size

---

## 9. Observability

- **Metrics:** Kafka consumer lag per topic/group, per-detector alert rate, end-to-end latency histogram, sensor uptime — exported via Prometheus-compatible metrics endpoint on each service.
- **Logging:** Structured JSON logs per service, correlation ID propagated from ingest through to alert for traceability.
- **Health endpoint:** Aggregated `/health` on the API layer pulls live metrics for the dashboard's health panel.
- **Alerting on the platform itself:** Operational alerts (not security alerts) for consumer lag exceeding threshold, sensor disconnect, or detection service crash-looping.

---

## 10. Testing Strategy

| Layer | Test approach |
|---|---|
| Feature extraction | Unit tests on windowing logic with synthetic time-stamped event sequences, including out-of-order/late-arrival cases |
| Detectors | Unit tests against known benign and known-attack feature vectors (from both synthetic and real-tool sources); regression suite re-run on every threshold/model change |
| DDoS sub-pattern | Explicit test cases confirming hping3 SYN/UDP floods classify as `volumetric_*` and Slowloris classifies as `slow_exhaustion` |
| End-to-end | Automated replay of labeled traffic scenarios (real-tool + synthetic) → evaluation harness computes precision/recall/F1/detection-delay per class, with ±2s tolerance for real-tool timestamp imprecision |
| Load/performance | Load-testing tool (Ostinato/TRex-driven) sweeps traffic rate, measures p50/p95/p99 latency and dropped-message count, run before every release |
| Architecture/security | Periodic review confirming no new outbound network path exists from the monitoring enclave or the lab environment; automated network-policy tests in CI where feasible |

---

## 11. Key Technical Risks

| Risk | Technical mitigation |
|---|---|
| Kafka partition skew causing hot-key bottlenecks | Composite partition keys, monitor per-partition lag, repartition strategy documented |
| Stateful feature extraction service crash losing in-memory windows | Periodic state checkpointing; acceptable to lose at most one window's worth of state (bounded by window size) |
| JA3 fingerprint evasion (randomized TLS fingerprints) | Treat as one signal among several; roadmap JA4 adoption; supplement with timing/size-based classifier that doesn't depend solely on fingerprint stability |
| Model drift degrading detection accuracy silently | Scheduled retraining + feature-distribution drift monitoring, alerting when baseline shifts significantly |
| Frontend WebSocket connection scaling with many concurrent analysts | Fan-out via a pub/sub layer (e.g., Redis pub/sub) between the alerts topic and WebSocket handlers if analyst concurrency grows beyond a single API instance's capacity |
| Real attack tools used in development create misuse/scope risk | Strict `lab-net` isolation, verified before use; tools never installed on non-isolated hosts; documented in `docs/lab-environment.md` |
| DGArchive access tier limits training data volume/diversity | DGA detector's rule-based entropy/n-gram gate remains fully functional independent of ML model quality; document achievable precision/recall honestly based on actual access tier obtained |
| Real-tool timestamp imprecision affects evaluation accuracy | Evaluation harness uses tolerance window (±2s) rather than exact-match; wrapper scripts capture start/end times as close to actual tool execution as possible |