# Product Requirements Document (PRD)
## Passive One-Way Network Threat Detection & Intelligence Platform

**Version:** 1.1 · **Status:** Draft · **Document owner:** [Product/Eng lead]

---

## 1. Executive Summary

A production-oriented system that passively monitors mirrored/diode-fed network traffic from critical infrastructure links and uses ML/statistical models to detect six classes of cyber threats in near real time, without any ability to interact with, probe, or act upon the monitored network. Output is structured, confidence-scored intelligence surfaced on a live analyst dashboard, with a standardized alert schema suitable for downstream SIEM/SOAR integration. The system is developed and validated against a mix of realistic synthetic traffic and real, purpose-built network tools operated inside an isolated lab environment, ensuring detection logic is proven against genuine attack-tool behavior rather than idealized synthetic patterns.

---

## 2. Problem Statement

Critical infrastructure operators use hardware data diodes or one-way traffic mirrors to feed monitoring enclaves, eliminating the risk of a compromised monitoring system pivoting into production networks. This architecture constrains any intelligence system to pure passive observation: no active probes, no handshake completion, no mitigation commands sent back across the ingest path. Most commercial and open-source detection tooling assumes at least some interactivity (active scanning, inline blocking, live queries to hosts). There is a need for a purpose-built detection platform engineered from the ground up for read-only, one-directional data, without compromising detection coverage across modern threat categories: DDoS, botnet C2, DGA/DNS tunnelling, encrypted-session malware, reconnaissance, and data exfiltration.

---

## 3. Goals & Non-Goals

**Goals**
- Detect and classify 6 threat categories from passively observed traffic only, with no ability to interact with monitored hosts
- Produce structured, evidence-backed alerts with calibrated confidence scores in near real time
- Operate as a continuously running streaming pipeline with bounded, monitored latency
- Sustain a defined, load-tested throughput target under production-like traffic volume
- Provide a live operational dashboard for SOC analysts to triage, investigate, and export alerts
- Support integration into existing security operations workflows (SIEM export, alert API)
- Validate detection logic against real, industry-standard traffic and attack tools, not solely idealized synthetic traffic, to ensure the system generalizes to real-world attack behavior

**Non-Goals**
- No intrusion prevention, active blocking, or inline mitigation of any kind
- No decryption of TLS/QUIC payloads
- No active probing, scanning, or querying of monitored hosts or networks
- Not a full case-management/ticketing SOAR platform — this is a detection and intelligence layer that feeds into one

---

## 4. Users & Personas

| Persona | Need |
|---|---|
| SOC Analyst (Tier 1/2) | Live, prioritized alert feed with clear evidence to triage quickly without false-positive fatigue |
| Security Engineer | Confidence in the architectural guarantee of no return path; ability to tune detection thresholds |
| Threat Intelligence Analyst | Ability to review evidence, correlate related alerts, and export findings |
| Platform/Infrastructure Owner | Assurance the system meets throughput/latency SLAs and won't become an attack surface itself |
| Compliance/Audit | Need for traceable, auditable alert evidence and clean chain-of-custody logging |

---

## 5. System Overview

```
Traffic Source (lab-generated/live) → One-way diode/mirror → Sensor Layer → Streaming Bus →
Feature Extraction (windowed, stateful) → Detection Layer (rule + ML) →
Alert Store → API Layer → Analyst Dashboard
                              │
                              └──► SIEM/export integration (optional downstream)
```

Hard architectural invariant, enforced at network, container, and application layers: no component downstream of the ingest point may ever initiate a connection back toward the traffic source, destination, or capture point. This invariant is validated in both the production deployment and the lab environment used for development/testing (see §7.1).

---

## 6. Functional Requirements

### 6.1 Ingest
- FR1: System shall ingest traffic as a strictly one-directional stream from a mirrored/diode source (live capture interface or replicated feed).
- FR2: System shall parse traffic into flow-level and protocol-level metadata (connection records, DNS, TLS/SSL handshake metadata) without requiring any return-path interaction.
- FR3: No code path in the system shall be capable of transmitting packets back toward the ingest source, destination hosts, or upstream network.
- FR4: System shall support multiple concurrent ingest sources (multi-sensor deployment) with per-sensor identification in all downstream records.

### 6.2 Feature Extraction
- FR5: System shall compute windowed statistical features per source/destination/flow key: rate, entropy, cardinality, inter-arrival timing, byte ratios.
- FR6: Windows shall be time-bounded (tumbling and sliding) and evaluated incrementally as data arrives, not only at batch/end-of-run boundaries.
- FR7: System shall maintain bounded memory through state eviction of idle keys, with configurable idle timeouts.
- FR8: Feature computation shall be deterministic — identical input streams shall always produce identical feature values, regardless of processing speed or replay timing.

### 6.3 Detection (per threat class)
- FR9: **DDoS/Volumetric** — detect SYN floods, UDP reflection/amplification, spoofed-source floods, and slow connection-exhaustion attacks (e.g., Slowloris-style) via rate deviation from baseline, source-IP entropy analysis, and long-duration low-throughput connection profiling. Alerts must indicate which sub-pattern (volumetric vs. slow-exhaustion) triggered detection.
- FR10: **C2 Beaconing** — detect periodic flows via inter-arrival regularity (coefficient of variation, autocorrelation) toward a small, stable set of destinations, including realistic jittered beacon timing.
- FR11: **DGA/DNS Tunnelling** — detect algorithmically generated domains via entropy/n-gram scoring against a trained baseline; detect tunnelling via query length, record-type distribution, and NXDOMAIN-rate anomalies.
- FR12: **Encrypted Malware** — detect via TLS/QUIC fingerprints (JA3/JA3S/JA4) matched against maintained threat-intelligence fingerprint lists, plus packet-size/timing sequence anomaly scoring, with zero payload decryption.
- FR13: **Reconnaissance/Scanning** — detect fan-out patterns (single source touching many destination ports/hosts) via approximate cardinality tracking.
- FR14: **Exfiltration** — detect asymmetric outbound/inbound byte-volume anomalies relative to a learned per-host baseline.
- FR15: Detection thresholds/model parameters shall be configurable per deployment without code changes (config-driven, not hardcoded).

### 6.4 Alerting
- FR16: Every detection shall produce a structured alert containing: unique ID, timestamp, sensor ID, flow identifier, threat class, severity, confidence score, and supporting evidence (triggering features/values, model used).
- FR17: Alerts shall be deduplicated and cooldown-throttled per (source, threat class) pair to prevent repeat-alert flooding for an ongoing condition.
- FR18: Alerts shall be published to a durable message stream prior to persistence, ensuring no alert loss on downstream storage failure.
- FR19: System shall support correlating multiple related alerts (same source, multiple threat signals) into a grouped incident view.
- FR20: System shall support alert export via API in a format suitable for SIEM ingestion (JSON, with optional CEF/STIX mapping as a stretch goal).

### 6.5 Dashboard / Analyst UI
- FR21: Dashboard shall display a live, auto-updating alert feed via persistent connection (WebSocket), with no manual refresh required.
- FR22: Each alert shall be visually severity-coded (critical/high/medium/low) and expandable to show full evidence detail.
- FR23: Dashboard shall support filtering and search by threat class, severity, source/destination, sensor, and time range.
- FR24: Dashboard shall display pipeline health metrics: ingest throughput, end-to-end alert latency, consumer lag, per-sensor status.
- FR25: Dashboard shall provide a historical view with time-range queries against stored alerts, not just the live feed.
- FR26: Dashboard shall support role-appropriate views (analyst triage view vs. engineering/health view) — at minimum as separate tabs/panels.
- FR27: Dashboard shall visually confirm system health of the one-way ingest architecture (sensor connectivity, no-egress status).

### 6.6 Administration & Configuration
- FR28: System shall provide a configuration interface (file-based or admin UI) for tuning per-detector thresholds, window sizes, and alert cooldowns.
- FR29: System shall support hot-reloading of threat-intelligence feeds (JA3 blocklists, DGA training data updates) without full pipeline restart.
- FR30: System shall log all configuration changes for auditability.

### 6.7 Evaluation & Quality Assurance
- FR31: System shall include an automated evaluation harness comparing generated alerts against labeled ground-truth traffic to compute precision, recall, F1, and detection delay per threat class.
- FR32: System shall include a load-testing capability measuring sustained throughput and p50/p95/p99 alert latency under configurable traffic rates.
- FR33: System shall support continuous regression testing of detection accuracy as models/thresholds are updated.
- FR34: Evaluation and validation shall include traffic generated by real, industry-standard tools (not solely synthetic/idealized traffic) to ensure detection logic generalizes to genuine attacker tooling.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency | End-to-end alert latency (event observed → alert visible) ≤ 15s at p95 under target load |
| Throughput | System shall sustain a defined production throughput target (flows/sec and Mbps), horizontally scalable via additional stream-processing partitions/consumers |
| Availability | Core ingest-to-alert pipeline shall target ≥99.5% uptime; sensor/dashboard outages must not cause silent data loss (buffered via durable streaming bus) |
| Reliability | Zero message loss under sustained load at stated throughput, verified via consumer-offset/drop tracking |
| Security | No component may possess any network path back toward the traffic source or destination; enforced at network, container, and code-review level, and validated in the isolated lab/test environment as well as production |
| Scalability | Architecture shall support horizontal scaling of feature extraction and detection layers independently as traffic volume grows |
| Determinism | Replaying identical traffic shall produce identical alerts (deterministic windowing via event-time watermarks) |
| Auditability | Every alert must be traceable to the specific features/evidence that produced it; no purely black-box scores without supporting evidence |
| Maintainability | Detectors shall be independently deployable/updatable modules, not a single monolith |
| Data retention | Alert and evidence data retained per configurable policy (e.g., 90 days hot, archived thereafter) |

### 7.1 Test/Lab Environment Requirement

All development-time traffic generation (benign and attack) shall occur within an isolated lab network with no route to production or public-internet-reachable infrastructure. Benign traffic is generated via iperf3 (sustained baseline) and Ostinato/TRex (protocol-realistic high-rate load, also used for throughput testing). Attack traffic is generated via real, purpose-built tools: hping3 (SYN/UDP floods), Slowloris (connection exhaustion), dnscat2/iodine (DNS tunnelling), DGArchive-sourced samples (DGA domains), and a sandboxed C2 emulator (realistic beacon timing/jitter). This requirement ensures the platform's detection logic is validated against genuine attack-tool behavior prior to any production deployment.

---

## 8. Data & Alert Schema

```json
{
  "schema_version": "1.0",
  "alert_id": "uuid",
  "timestamp": "ISO8601",
  "sensor_id": "string",
  "threat_class": "ddos | c2_beacon | dga | dns_tunnel | encrypted_malware | recon | exfiltration",
  "severity": "low | medium | high | critical",
  "confidence": 0.0,
  "evidence": {
    "features_triggered": ["..."],
    "feature_values": {},
    "model": "string",
    "pattern": "string (optional, e.g. 'volumetric_syn' | 'slow_exhaustion' for ddos)"
  },
  "observation_window": ["start_ts", "end_ts"],
  "related_alerts": ["alert_id", "..."],
  "status": "new | acknowledged | investigating | resolved | false_positive"
}
```

`evidence.pattern` added to support sub-classification within a threat class (e.g., distinguishing a volumetric SYN flood from a Slowloris-style slow exhaustion attack, both classified under `ddos`).

---

## 9. System Architecture — Backend

| Component | Technology | Responsibility |
|---|---|---|
| Sensor layer | Zeek (or equivalent NSM parser) | Parses live/mirrored traffic into conn/dns/ssl records, computes JA3/JA3S |
| Streaming bus | Kafka (or equivalent, e.g. Redpanda) | Decouples ingest from processing; durable, replayable, horizontally scalable |
| Feature extraction service | Python/JVM stream processors | Stateful windowed feature computation per key, partitioned by flow/source key |
| Detection service(s) | Python (scikit-learn, LightGBM, or equivalent) | Independently deployable detector per threat class; rule-based gates + ML scoring |
| Threat-intel feed manager | Scheduled service | Ingests/updates JA3 blocklists, DGArchive-derived training data, refreshes models |
| Alert store | TimescaleDB (or equivalent time-series store) | Persists alerts with efficient time-range querying |
| API layer | REST + WebSocket service (e.g. FastAPI) | Serves alert history, live stream, config endpoints, health metrics |
| Auth/access control | Standard auth provider (OAuth2/OIDC or equivalent) | Analyst login, role-based access to admin functions |
| Lab/test traffic environment | iperf3, Ostinato/TRex, hping3, Slowloris, dnscat2, iodine, C2 emulator, DGArchive samples | Generates realistic and attack-tool-authentic traffic for development, validation, and evaluation |

### Deployment model
- Each service containerized independently, orchestrated via Kubernetes or Docker Compose for smaller deployments
- Detection services scale horizontally per threat class based on load
- Streaming bus partitioned by flow key to enable parallel consumption without losing per-key ordering guarantees
- Lab/test environment isolated from production deployment network at all times

---

## 10. System Architecture — Frontend

| Component | Technology | Responsibility |
|---|---|---|
| Framework | React (with a build tool such as Vite) | SPA analyst dashboard |
| Real-time layer | WebSocket client | Live alert feed without polling |
| State management | Centralized store (e.g. Zustand/Redux) as complexity grows | Alert list, filters, selected alert, user session |
| Visualization | Charting library (e.g. Recharts/D3) | Alert volume timelines, throughput/latency graphs, network fan-out views |
| Styling/design system | Dark, high-density SOC-style theme with a consistent severity color system | Fast visual triage under alert volume |
| Routing | Client-side router | Separate views: live feed, historical search, incident view, health/admin panel |

### Key UI views
1. **Live alert feed** — primary triage view, auto-updating, severity-coded
2. **Alert detail/evidence panel** — full feature breakdown, model used, related alerts, sub-pattern where applicable
3. **Historical search** — time-range and filtered queries against stored alerts
4. **Incident/correlation view** — grouped alerts by source representing a multi-signal attack
5. **Pipeline health dashboard** — throughput, latency, per-sensor and per-detector status
6. **Admin/configuration panel** — threshold tuning, threat-intel feed status, user/role management

---

## 11. Detection Approach Summary (per class)

| Threat | Primary Signal | Method | Validation Traffic Source |
|---|---|---|---|
| DDoS | Rate deviation from baseline, source-IP entropy, SYN/no-ACK ratio; long-duration low-throughput connection profile | Statistical baseline (EWMA/change-point detection) + IsolationForest anomaly layer | hping3 (SYN/UDP flood), Slowloris (connection exhaustion) |
| C2 Beacon | Inter-arrival coefficient of variation, destination fan-in | Statistical periodicity scoring, clustering for campaign grouping | Sandboxed C2 emulator (configurable interval/jitter) |
| DGA/Tunnel | Domain entropy, n-gram likelihood, NXDOMAIN ratio, query-length/type anomalies | Supervised classifier (LightGBM), trained/validated on labeled DGA corpora | DGArchive (DGA domains), dnscat2/iodine (tunnelling) |
| Encrypted malware | JA3/JA3S/JA4 fingerprint, packet timing/size sequence | Threat-intel fingerprint match + anomaly scoring on fingerprint rarity | External threat-intel feed (JA3 blocklist) |
| Recon/Scan | Destination fan-out cardinality, failure ratio | Approximate cardinality tracking (HyperLogLog) + adaptive thresholds | Synthetic (Scapy) |
| Exfiltration | Outbound/inbound byte ratio, novel-destination signal | Per-host baseline with statistical anomaly detection (z-score) | Synthetic (Scapy/iperf3 reverse-mode) |

Design principle: every detector implements a rule/statistical baseline independently of its ML layer, so ML degradation or retraining never removes baseline detection capability for that class. Where a real attack tool exists for a threat class, it is used in preference to synthetic traffic to ensure detection logic is validated against authentic attacker behavior.

---

## 12. Success Metrics (Production)

- Detection coverage: all 6 threat classes operational and independently monitorable, validated against both synthetic and real-tool-generated traffic
- Precision/Recall per class tracked continuously via the evaluation harness against labeled traffic samples, including DGArchive-sourced real malware-family domains for the DGA detector
- Sustained throughput meets or exceeds the defined production target with p95 latency ≤ 15s, measured using Ostinato/TRex-generated load
- Zero data loss at target throughput, verified continuously
- False-positive rate tracked per class and kept within an agreed operational threshold (to avoid analyst alert fatigue)
- DDoS detector correctly distinguishes volumetric (SYN/UDP flood) from slow-exhaustion (Slowloris) sub-patterns
- Mean time from alert generation to analyst acknowledgment (dashboard usability proxy)
- System uptime against the defined availability SLA

---

## 13. Security & Architectural Validation

- Network segmentation between ingest/monitoring enclave and any external system shall be enforced at the infrastructure level (firewall rules, one-way network configuration), not solely via application logic
- The lab/test environment used for development and validation shall be isolated from any production or public-internet-reachable network, given that real attack tools (hping3, Slowloris, dnscat2, iodine) are used to generate test traffic
- Regular architecture reviews shall confirm no new code path introduces an outbound connection toward monitored infrastructure
- Threat-intelligence feed updates (JA3 blocklists, DGArchive-derived training data) shall be pulled from external sources on a separate, isolated update path that does not touch the monitoring enclave's ingest network
- All configuration changes and model updates shall be logged for audit and rollback
- DGArchive data usage shall comply with its access terms and licensing; access tier and license notes shall be tracked in the threat-intel feed metadata store

---

## 14. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| High false-positive rate causing alert fatigue | Per-class threshold tuning, cooldown/dedupe logic, continuous precision/recall monitoring, feedback loop from analyst-marked false positives |
| Traffic volume exceeds tested throughput in production | Horizontal scaling design from day one (partitioned streaming bus, independently scalable detector services) |
| Model drift as network baselines change over time | Scheduled retraining/baseline refresh cadence, drift monitoring on feature distributions |
| Threat-intel feed staleness (JA3 blocklists, DGArchive corpora) | Automated scheduled feed refresh with staleness alerting |
| Encrypted traffic evolving beyond current fingerprinting methods (e.g. JA3 randomization) | Plan migration path to JA4 and monitor fingerprinting research; treat fingerprint matching as one signal among several, not sole detection method |
| Single point of failure in streaming bus | Deploy Kafka/bus in a replicated, fault-tolerant configuration |
| Real attack tools (hping3, Slowloris, dnscat2, iodine) used in development pose misuse/scope risk | Strict lab network isolation with no route to real infrastructure; documented, verified isolation checklist before any attack tool is run; team acknowledgment of acceptable-use terms |
| DGArchive access/licensing constraints limit training data availability | Confirm access tier early; document access level and license terms in threat-intel feed metadata; design DGA detector to remain functional (rule-based fallback) even with limited ML training data |

---

## 15. Out of Scope (v1)

- Automated response/mitigation of any kind (by design, per the diode constraint)
- Payload decryption or content inspection
- Full SOAR-style case management and ticketing workflows (integration point only)
- Multi-tenant architecture (single-organization deployment assumed for v1)
- Automatic threat-intel feed generation (consumes external feeds, does not produce them)
- Running attack-tool traffic generation against any non-lab, non-isolated target

---

## 16. Open Questions

- What is the target production throughput ceiling for the initial deployment, and what traffic profile should the load-testing suite model against?
- Should the platform support on-prem-only deployment, or is a cloud-hosted analyst dashboard acceptable given the enclave's isolation requirements?
- What SIEM/SOAR systems need to be supported for alert export in v1 vs. later phases?
- What data retention and compliance requirements apply to captured metadata and alert evidence?
- What access tier to DGArchive is realistically obtainable, and does it materially affect the DGA detector's achievable precision/recall targets?