# plan.md

## Project: Passive One-Way Network Threat Detection & Intelligence Platform

This document is the build plan and methodology for building this project. Follow phases in order — do not skip ahead. Each phase has a concrete, verifiable exit condition. Do not proceed to the next phase until the current one's exit condition is met.

---

## 0. Ground Rules (read first)

- **Build in vertical slices, not layers.** Get one full path (traffic → sensor → bus → detector → alert → storage → API → dashboard) working end-to-end before adding the second detector. Never build "all of the backend" then "all of the frontend."
- **Rules before ML.** Every detector must work as a threshold/statistical gate first. ML is added as an enhancement layer afterward, never a blocker for a detector being "done."
- **No component may ever open an outbound connection back toward the traffic source.** This is a hard constraint — enforce it in network configuration, not just in code comments.
- **State real, tested numbers.** Every performance claim in documentation must come from an actual load-test run, not an estimate.
- **Every phase ends with something runnable.** If a phase is "complete" but nothing can be executed/demoed, it isn't complete.
- **Real attack tools, isolated lab only.** All traffic generation — benign and attack — runs inside an isolated network namespace with no route to any real infrastructure. This is verified, not assumed, before any attack tool is run.

---

## 1. Repository Structure (create first, exactly this)

```
threatpipe/
├── generator/
│   ├── benign/
│   │   ├── run_iperf3.sh          # sustained TCP/UDP baseline
│   │   └── run_ostinato_trex.py   # mixed protocol realistic load + throughput testing
│   ├── attacks/
│   │   ├── run_hping3_synflood.sh
│   │   ├── run_hping3_udpflood.sh
│   │   ├── run_slowloris.py
│   │   ├── run_dnscat2_tunnel.sh
│   │   ├── run_iodine_tunnel.sh
│   │   ├── dga_dgarchive_replay.py   # replays labeled DGArchive domain lists as DNS queries
│   │   ├── c2_emulator_beacon.py     # sandboxed C2 emulator wrapper, configurable interval/jitter
│   │   ├── scan_portsweep.py         # Scapy — recon/port scan
│   │   └── exfil_bulk_upload.py      # Scapy or iperf3 reverse-mode — exfiltration
│   └── manifests/
│       └── wave_N_manifest.jsonl     # ground truth: {tool, type, start_ts, end_ts, src, dst}
├── sensor/            # Zeek config/output
├── ingest/             # Zeek log → Kafka producer
├── pipeline/
│   ├── features/       # windowed feature extraction
│   ├── detectors/       # one file per threat class
│   └── alerts/          # schema, dedupe, sink to DB
├── api/                 # FastAPI REST + WebSocket
├── dashboard/            # React frontend
├── tools/                 # loadtest.py, evaluate.py
├── docs/
│   ├── architecture.md
│   ├── models.md
│   ├── throughput.md
│   └── lab-environment.md   # tool inventory + isolation/safety guarantees
├── docker-compose.yml
└── plan.md               # this file
```

---

## 2. Phase 0 — Lab Environment Setup (do this before Phase 1)

**Goal:** An isolated network environment exists, with no route to real infrastructure, capable of hosting both traffic generators and the sensor's mirror/SPAN capture point.

**Steps:**
1. Create a dedicated Docker network (or VLAN) — `lab-net` — with no route to any production, corporate, or public-internet-reachable network.
2. Confirm no component in `lab-net` has outbound internet access, except a separately isolated threat-intel update path (used only in Phase 4 for pulling JA3 blocklists/DGArchive data).
3. Install and pin versions for: iperf3, Ostinato or TRex, hping3, Slowloris, dnscat2, iodine, and the sandboxed C2 emulator — all inside `lab-net` containers/VMs, never on a host machine with broader network access.
4. Set up the mirror/SPAN mechanism from `lab-net`'s gateway into the Zeek sensor — this replicates the same one-way ingest pattern the platform is designed for in production.
5. Write `docs/lab-environment.md` documenting the topology, tool inventory, and safety boundaries (see §9 for required contents).
6. Record team acknowledgment that these are real attack tools, used only within `lab-net`, consistent with standard security-research practice.

**Exit condition:** `docker network inspect` (or equivalent) confirms `lab-net` has no route out; mirror capture confirmed reaching the Zeek sensor with a basic test packet.

---

## 3. Phase 1 — Prove the Full Pipeline (Plumbing First)

**Goal:** One fake/placeholder alert travels from a captured packet all the way to a live dashboard. No real detection logic yet.

**Steps:**
1. Write `docker-compose.yml` with services: Kafka, TimescaleDB, Zeek (kept alive via `tail -f /dev/null`), API, dashboard — all attached to `lab-net` where relevant.
2. Verify all containers start and are reachable (`docker ps`, basic connectivity checks on each).
3. Run `generator/benign/run_iperf3.sh` — produces 60s of sustained TCP/UDP benign traffic across the mirror interface into Zeek.
4. Confirm Zeek produces `conn.log`, `dns.log`, `ssl.log` from this live traffic.
5. `ingest/producer.py` — parses Zeek TSV logs, converts to JSON, publishes to Kafka topics `events.conn`, `events.dns`, `events.tls`.
6. `pipeline/detectors/placeholder.py` — consumes `events.conn`, fires exactly one hardcoded fake alert on the first message it sees, publishes to `alerts` topic.
7. `pipeline/alerts/sink.py` — consumes `alerts` topic, writes to TimescaleDB `alerts` table.
8. `api/main.py` — FastAPI app with `GET /alerts` (reads from DB) and `WS /ws/alerts` (live pushes from Kafka consumer).
9. `dashboard/` — React app, connects to `/ws/alerts`, renders alerts as a plain list (no styling yet).

**Exit condition:** Running iperf3 → Zeek → producer chain results in one alert visibly appearing on the dashboard in the browser, live, without manual refresh.

---

## 4. Phase 2 — Real Detectors (Build in This Order)

Build each detector as its own file in `pipeline/detectors/`, following the exact same consume→compute→publish shape as the Phase 1 placeholder. Replace the placeholder once the first real detector works.

**Order and traffic source per detector:**

| Order | Detector | Traffic tool(s) | Core signal |
|---|---|---|---|
| 1 | Recon/Port scan | `scan_portsweep.py` (Scapy) | Distinct dst-port fan-out per src over 60s window (threshold-based) |
| 2 | DDoS | `run_hping3_synflood.sh`, `run_hping3_udpflood.sh`, `run_slowloris.py` | Rate deviation from EWMA baseline + source-IP entropy + SYN/no-ACK ratio (volumetric); long-duration low-pps connection profile (Slowloris) |
| 3 | Encrypted malware | JA3 blocklist (logic-only, no traffic generator needed) | JA3 exact-match against a static blocklist file |
| 4 | DGA/DNS tunnelling | `dga_dgarchive_replay.py` (DGArchive samples), `run_dnscat2_tunnel.sh`, `run_iodine_tunnel.sh` | Domain entropy/n-gram score (DGA); query length/record-type/NXDOMAIN anomalies (tunnelling) |
| 5 | C2 beaconing | `c2_emulator_beacon.py` (sandboxed C2 emulator) | Inter-arrival coefficient of variation over rolling window |
| 6 | Exfiltration | `exfil_bulk_upload.py` (Scapy or iperf3 reverse-mode) | Outbound/inbound byte ratio z-score per host baseline |

**For each detector:**
1. Wrap the tool invocation with start/end timestamp capture, appended to `generator/manifests/wave_N_manifest.jsonl` as `{tool, type, start_ts, end_ts, src, dst}` — real tools don't self-report this, the wrapper must.
2. Implement the detector against the pipeline's existing feature/event stream.
3. Run the scenario end-to-end, confirm the correct alert appears on the dashboard with correct `threat_class` and non-trivial `evidence`.
4. For the DDoS detector specifically: confirm all 3 sub-patterns (SYN flood, UDP flood, Slowloris exhaustion) are correctly classified as `ddos`, with `evidence` distinguishing which sub-pattern triggered it (e.g. `"pattern": "slow_exhaustion"` vs `"pattern": "volumetric_syn"`).
5. Do not proceed to the next detector until the current one produces a correct alert on its target scenario **and** produces no alert on a pure-benign (iperf3/Ostinato) scenario.

**Exit condition:** All 6 detectors independently fire correctly against their respective real-tool-generated attack scenarios, and stay silent on benign-only traffic.

---

## 5. Phase 3 — Feature Extraction Hardening

**Goal:** Move from ad-hoc per-detector state to a shared, windowed feature-extraction layer.

**Steps:**
1. `pipeline/features/windowing.py` — implement tumbling (60s) and sliding (10-min, 30s hop) window managers with event-time watermarking (watermark = max seen timestamp − 10s).
2. Move each detector's inline state tracking into this shared feature layer, publishing to `features.*` Kafka topics.
3. Add LRU eviction for idle keys (>30 min) and HyperLogLog for cardinality-heavy features (via `datasketch`).
4. Re-run all 6 attack scenarios — confirm identical detection results as before this refactor (proves determinism and non-regression).

**Exit condition:** All detectors consume from `features.*` topics instead of raw events; results match pre-refactor behavior exactly on the same replayed scenarios.

---

## 6. Phase 4 — ML Layer (Additive Only)

**Goal:** Add ML scoring on top of existing rule-based detectors — never replace the rule baseline.

**Steps:**
1. Train a LightGBM classifier for DGA detection on **DGArchive family-labeled domain samples** + Tranco top-1M as the benign class. Confirm and record the DGArchive access tier obtained (public sample vs. research-request access) before committing to it as the primary training source.
2. Train an IsolationForest per detector family (DDoS, scan, exfil) on benign-traffic feature vectors from `iperf3`/`Ostinato`/`TRex` baseline captures.
3. Wire each detector to combine its rule-based gate output with the ML model's anomaly/confidence score (e.g., `confidence = max(rule_score, calibrated_ml_score)`).
4. Document training data, features used, and validation method in `docs/models.md`: leave-one-DGA-family-out cross-validation (now against real malware families) for DGA; contamination-rate tuning for IsolationForest.

**Exit condition:** Each of the 6 detectors produces a calibrated `confidence` score informed by both rule and ML signal; documentation of training/validation exists, citing DGArchive appropriately.

---

## 7. Phase 5 — Dashboard & UX Build-Out

Build these incrementally, matched to detectors already live — don't wait until the end.

| Component | Depends on |
|---|---|
| Live alert feed (severity-colored) | Phase 1 |
| Evidence detail drawer | Any real detector (Phase 2) |
| Threat-class filter tabs | ≥2 detectors live |
| Timeline chart of alert volume | Any detector producing repeated alerts |
| Pipeline health panel (throughput/latency/lag) | Phase 3 (features layer emits metrics) |
| Incident/correlation view (group alerts by source) | ≥3 detectors live simultaneously |

**Exit condition:** All 6 components implemented and functioning against live data, dark SOC-style theme applied consistently, severity colors consistent throughout.

---

## 8. Phase 6 — Evaluation & Load Testing

**Steps:**
1. `tools/evaluate.py` — replays all scenario captures, joins generated alerts against ground-truth manifests (from the real-tool wrapper scripts) by time+tuple overlap, outputs per-class precision/recall/F1/detection-delay to `eval_report.md`. Use a wider matching tolerance window (e.g. ±2s) than exact-match, since real-tool timestamps are coarser than a scripted scenario's.
2. `tools/loadtest.py` — use **Ostinato or TRex** to generate sustained synthetic traffic at increasing rates (e.g. 50/250/500/1000 flows/sec), measuring p50/p95/p99 end-to-end alert latency, Kafka consumer lag, and dropped-message count at each rate.
3. Record the actual sustained rate achieved with zero drops — this is the number that goes in documentation, not a target or estimate.
4. Tune detector thresholds against false-positive rate using the evaluation harness results.

**Exit condition:** `eval_report.md` and a throughput report exist with real measured numbers; thresholds have been tuned at least once based on this data.

---

## 9. Phase 7 — Documentation & Packaging

**Steps:**
1. `docs/architecture.md` — system diagram, explanation of the one-way constraint and how it's enforced (network config, not just code).
2. `docs/models.md` — features per detector, training data (including DGArchive citation and access tier), validation approach, per-class metrics from Phase 6.
3. `docs/throughput.md` — load-test methodology (Ostinato/TRex) and results.
4. `docs/lab-environment.md` — must include: network topology of `lab-net`, full tool inventory with pinned versions, explicit statement that attack tools are never run against non-lab targets, and a verification checklist (no route out of `lab-net`, tools confirmed lab-only, mirror capture confirmed, team acknowledgment recorded).
5. `README.md` — setup instructions, how to run the full stack, how to run a demo scenario end-to-end.

**Exit condition:** A new developer can clone the repo, follow the README, and get a working alert on the dashboard without any additional guidance. `docs/lab-environment.md` verification checklist fully checked off.

---

## 10. Definition of Done (whole project)

- [ ] All 6 threat classes detected correctly against real-tool-generated scenarios, silent on benign traffic
- [ ] DDoS detector correctly distinguishes SYN flood / UDP flood / Slowloris sub-patterns
- [ ] Shared windowed feature-extraction layer in place, deterministic on replay
- [ ] ML layer additive on top of every detector, documented; DGA model trained on DGArchive with access tier recorded
- [ ] Dashboard shows live feed, evidence detail, filters, timeline, health panel, incident view
- [ ] Evaluation harness produces real precision/recall/F1 numbers against real-tool traffic
- [ ] Load test (via Ostinato/TRex) produces a real, documented sustained throughput number with p95 latency ≤15s
- [ ] Lab network isolation verified — attack-tool traffic generation confirmed to have no route to real infrastructure
- [ ] No code path anywhere sends traffic back toward the ingest source (verified via network config review)
- [ ] Full documentation set complete and accurate to what was actually built, including `docs/lab-environment.md`

---

## 11. Execution Note

Work phase by phase, in order, starting with Phase 0 (lab environment) before any traffic generation occurs. After completing each phase, explicitly state which exit condition was met and how it was verified (command run, output observed) before starting the next phase. If a step in a phase fails, fix it within that phase before moving on — do not carry forward known-broken components into later phases.