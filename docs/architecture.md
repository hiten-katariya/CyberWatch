# System Architecture & Technical Specifications

## Passive One-Way Network Threat Detection & Intelligence Platform

### 1. Architectural Principles

1. **Strict One-Way Passive Monitoring**: All network traffic is captured via a hardware data diode or passive mirror/SPAN port into the Zeek sensor. No component downstream of the sensor has an outbound route or interface to initiate network communication back toward monitored traffic sources.
2. **Decoupled Event & Feature Stream**: Zeek log data is ingested and normalized into Kafka event streams (`events.conn`, `events.dns`, `events.tls`). A single shared service `feature-extractor` computes windowed statistical features and publishes them to `features.*` topics.
3. **Decoupled Rule & Statistical Threat Detectors**: 7 real threat detectors execute asynchronously in parallel, each subscribing to its relevant feature or event stream, evaluating configurable thresholds from `config/detectors.yaml`, and publishing canonical alerts to the `alerts` topic.
4. **Resilient Persistence & Dual User Interfaces**: An alert worker (`alert-sink`) stores canonical alerts in TimescaleDB. The FastAPI backend exposes REST endpoints (`/health`, `/alerts`, `/alerts/stats`, `/alerts/{id}`) and WebSocket broadcasts (`/ws/alerts`). The React SOC Analyst Dashboard provides live streaming feed, evidence drawers, threat filters, and timelines, while Grafana provides long-term operational analytics and historical trends.

---

### 2. Pipeline Flow

```text
Benign & Attack Lab Traffic
          │
          ▼
   Mirror / SPAN
          │
          ▼
     Zeek Sensor
          │
          ▼
    Ingest Adapter (ingest/producer.py)
          │
          ├──► events.conn ──┐
          ├──► events.dns  ──┼──► Feature Extractor (pipeline/features/extractor.py)
          └──► events.tls  ──┘            │
                                          ▼
                                     features.*
                                          │
    ┌────────────────┬────────────────────┼───────────────────┬────────────────┐
    │                │                    │                   │                │
    ▼                ▼                    ▼                   ▼                ▼
Recon Detector  DDoS Detector     C2 Beacon Detector   Exfiltration Detector (features.conn)
 (recon.py)       (ddos.py)          (c2_beacon.py)      (exfiltration.py)
    │                │                    │                   │
    └────────────────┼────────────────────┼───────────────────┘
                     │                    │
                     ▼                    ▼
                DGA Detector    DNS Tunnel Detector (events.dns)
                 (dga.py)        (dns_tunnel.py)
                     │                    │
                     └────────────────────┤
                                          │
                                          ▼
                               Encrypted Malware Detector (events.tls)
                                 (encrypted_malware.py)
                                          │
                                          ▼
                                 Kafka (alerts topic)
                                          │
                                ┌─────────┴─────────┐
                                ▼                   ▼
                           Alert Sink            FastAPI Backend
                                │                   │
                                ▼                   ├──► WS /ws/alerts ──► React SOC UI
                           TimescaleDB              └──► GET /alerts   ──► (port 3000)
                                │
                                ▼
                             Grafana (port 3001)
```

---

### 3. Detector Catalog & Thresholds

| Detector | Script | Input Stream | Core Signals & Evidence | Config File Key |
|---|---|---|---|---|
| Reconnaissance | `pipeline/detectors/recon.py` | `features.conn` | Port & host fan-out cardinality over 10s windows | `recon` |
| DDoS | `pipeline/detectors/ddos.py` | `features.conn` | Sub-patterns: `volumetric_syn`, `volumetric_udp`, `slow_exhaustion` | `ddos` |
| DGA | `pipeline/detectors/dga.py` | `events.dns` | Shannon entropy, length, digit ratio, n-gram lexical analysis | `dga` |
| DNS Tunnelling | `pipeline/detectors/dns_tunnel.py` | `events.dns` | Query length, label length, entropy, TXT/NULL qtypes (`dnscat2`, `iodine`) | `dns_tunnel` |
| C2 Beaconing | `pipeline/detectors/c2_beacon.py` | `features.conn` | Inter-arrival mean, stddev, coefficient of variation (`periodic_beacon`) | `c2_beacon` |
| Encrypted Malware | `pipeline/detectors/encrypted_malware.py` | `events.tls` | JA3 / JA3S / JA4 threat-intel blocklist matching | `encrypted_malware` |
| Exfiltration | `pipeline/detectors/exfiltration.py` | `features.conn` | Outbound/inbound byte ratio & sustained high volume transfers | `exfiltration` |
