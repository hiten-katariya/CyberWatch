# Passive One-Way Network Threat Detection & Intelligence Platform

## Phase 1 — Proven End-to-End Pipeline

This platform implements a passive, one-way network threat detection architecture. Phase 1 demonstrates and verifies that benign network traffic flows through the complete pipeline end-to-end:

```text
Benign Traffic (iperf3)
       ↓
Mirror / Capture Interface
       ↓
Zeek Sensor
       ↓
Zeek Logs (conn.log, dns.log, ssl.log)
       ↓
Ingest Adapter (ingest/producer.py)
       ↓
Kafka (events.conn, events.dns, events.tls)
       ↓
Placeholder Detector (pipeline/detectors/placeholder.py)
       ↓
Kafka (alerts)
       ↓
Alert Sink (pipeline/alerts/sink.py)
       ↓
TimescaleDB (alerts table)
       ↓
FastAPI Backend (api/main.py)
       ↓
WebSocket (/ws/alerts)
       ↓
React Dashboard (dashboard/)
```

---

## 1. Prerequisites

- **Docker Desktop** (with WSL2 backend on Windows)
- **Python 3.13+**
- **Node.js v22+**

---

## 2. Quick Start

### Start the Docker Services

Launch all 8 services in the isolated `lab-net` network:

```bash
docker compose up -d --build
```

Verify all services are running:

```bash
docker compose ps
```

Services started:
- `sih-kafka`: Apache Kafka 3.8.0 (KRaft mode)
- `sih-timescaledb`: TimescaleDB (PostgreSQL 16)
- `sih-zeek`: Zeek network monitor
- `sih-ingest`: Log tailer & event normalizer
- `sih-placeholder-detector`: Phase 1 test detector
- `sih-alert-sink`: TimescaleDB alert persistence worker
- `sih-api`: FastAPI REST API & WebSocket server
- `sih-dashboard`: React SOC Analyst Dashboard

---

## 3. Running the Phase 1 Benign Demo & Verification

### Option A: Automated End-to-End Test

Run the full end-to-end verification script:

```bash
python tools/verify_pipeline.py
```

### Option B: Benign Traffic Generation

Run the benign traffic generator:

```bash
bash generator/benign/run_iperf3.sh 127.0.0.1 60
```
*(or Python fallback: `python generator/benign/gen_traffic.py --duration 60`)*

### Verify Network Isolation

Check that `lab-net` is isolated and all containers are attached:

```bash
python tools/verify_lab_net.py
```

---

## 4. Accessing Services

- **React Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI REST API**: [http://localhost:8000/alerts](http://localhost:8000/alerts)
- **FastAPI Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Live WebSocket Stream**: `ws://localhost:8000/ws/alerts`

---

## 5. Running Automated Tests

Run unit tests:

```bash
python -m pytest tests/
```

---

## 6. Stopping the Environment

To stop and remove containers and network:

```bash
docker compose down
```

---

## 7. Troubleshooting

- **Check logs of a service**:
  ```bash
  docker compose logs -f api
  docker compose logs -f placeholder-detector
  docker compose logs -f alert-sink
  ```
- **Inspect network isolation**:
  ```bash
  docker network inspect sih_lab-net
  ```
