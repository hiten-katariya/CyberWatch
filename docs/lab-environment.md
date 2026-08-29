docs/lab-environment.md

Lab Environment & Traffic Generation Safety Document

Passive One-Way Network Threat Detection & Intelligence Platform

Version: 1.1 · Status: Updated · Companion to: PRD v1.1, Technical Design Document v1.1, Build Plan

1. Purpose

This document defines the isolated development and test environment used to generate benign and attack traffic for developing, testing, evaluating, and validating the Passive One-Way Network Threat Detection & Intelligence Platform.

Because the project validates detection logic using real, industry-standard network tools rather than only idealized synthetic traffic, this document makes the safety boundaries explicit, verifiable, and auditable.

It covers:

Lab network topology and isolation

Windows/Docker-based development setup

Benign and attack traffic-generation tooling

Ground-truth capture and data provenance

Threat-intelligence update-path isolation

Safety and acceptable-use requirements

Pre-run verification procedures

Incident handling for accidental network misconfiguration

Environment change tracking

This document applies only to the development/testing lifecycle. Production traffic is expected to arrive through a genuine hardware data diode or mirror/SPAN interface.

2. Scope

The environment supports the following project activities:

Phase 0: Isolated lab environment setup and verification

Phase 1: End-to-end pipeline validation using benign traffic — **VERIFIED PASS**

Phase 2: Per-threat-class detector development and testing

Phase 3: Feature-extraction hardening and replay validation

Phase 4: ML model training and validation, including DGArchive samples and C2-emulator output

Phase 5: SOC dashboard validation against live detector output

Phase 6: Evaluation and load testing using Ostinato/TRex

Phase 7: Documentation and packaging

The environment does not represent the production network. Production deployment uses real mirrored/diode-fed infrastructure rather than lab-generated traffic.

3. Host and Container Environment

3.1 Development Host

The current development workflow is Windows-oriented:

Windows host machine

WSL2

Docker Desktop for Windows

Docker Desktop configured to use the WSL2 backend

The host is used for development and container orchestration. Real attack tools must not be installed or executed directly on a host that has broader network reachability.

3.2 Container Isolation

Traffic-generation tools are executed inside dedicated containers/VMs attached to lab-net.

The intended separation is:

Windows Developer Host
        │
        ├── WSL2
        │
        └── Docker Desktop
              │
              ├── lab-net
              │    ├── benign generators
              │    ├── attack generators
              │    └── isolated test targets
              │
              └── monitoring services
                   └── Zeek receives mirror copy only

The exact Docker Compose service topology may evolve with implementation, but the one-way/no-egress security invariant must not change.

4. Network Topology

┌──────────────────────────── lab-net (ISOLATED) ────────────────────────────┐
│                                                                           │
│  [Benign Traffic Generators]       [Attack Traffic Generators]            │
│   iperf3                            hping3                                 │
│   Ostinato / TRex                  Slowloris                              │
│                                     dnscat2                               │
│                                     iodine                                │
│                                     C2 emulator                           │
│                                     Scapy scripts                         │
│                                                                           │
│                    ┌──────────────────────────┐                           │
│                    │ Isolated Test Targets    │                           │
│                    └────────────┬─────────────┘                           │
│                                 │                                         │
│                                 ▼                                         │
│                    [Mirror / SPAN Gateway]                               │
│                         one-way copy only                                 │
└─────────────────────────────────┼─────────────────────────────────────────┘
                                  │
                                  ▼
                         [Zeek Sensor]
                     mirror copy / ingest only
                     NO PATH BACK TO lab-net

                    ║ separate network path ║

              [Threat-Intel Update Environment]
                 JA3/JA4 feeds + DGArchive
                         │
                         ▼
                  Internet access only

4.1 Isolation Properties

lab-net must:

Have no route to production, corporate, or public-internet-reachable infrastructure.

Contain only explicitly provisioned lab generators and targets.

Prevent traffic-generation containers from reaching the public internet.

Feed the Zeek sensor through a strictly one-directional mirror/SPAN path.

Prevent the Zeek sensor and all downstream monitoring services from initiating connections back toward lab traffic sources or monitored targets.

Keep threat-intelligence retrieval on a separate network path that does not overlap with lab-net or the ingest/mirror path.

The one-way property is an architectural invariant and must be enforced through network configuration, container networking, and verification—not merely through application code.

5. Tool Inventory

Tool / Source

Category

Purpose / Threat Class

Version

iperf3

Benign traffic

Sustained TCP/UDP baseline; baseline for detector testing

[pin before use]

Ostinato

Benign / load testing

Protocol-realistic mixed traffic; controlled pps/bps load

[pin before use]

TRex

Benign / load testing

High-rate traffic generation and throughput testing; alternative/supplement to Ostinato

[pin before use]

hping3

Attack tool

DDoS: SYN flood, UDP flood, spoofed-source flood scenarios

[pin before use]

Slowloris

Attack tool

DDoS: slow connection-exhaustion scenario

[pin before use]

dnscat2

Attack tool

DNS tunnelling scenario

[pin before use]

iodine

Attack tool

DNS tunnelling alternate implementation

[pin before use]

Sandboxed C2 emulator

Controlled internal tool

C2 beacon timing/jitter detection scenario

[internal build/version]

DGArchive samples

Labeled dataset

DGA domain-generation detection and ML training/validation

[access date/tier]

Scapy

Custom scripting

Recon/port-scan and exfiltration test scenarios

[pin before use]

Zeek

Sensor

Passive protocol/flow metadata extraction

[pin before use]

5.1 Tool Placement Rule

All real attack tools—specifically hping3, Slowloris, dnscat2, and iodine—must be installed and executed only inside the isolated lab containers/VMs.

They must never be installed or executed on:

A developer laptop/host with broader network access

Production systems

Corporate networks

Public cloud targets unless explicitly provisioned as isolated lab targets

Public internet hosts

Any third-party system

6. Traffic Scenarios and Ground Truth

The lab is designed to exercise the six detection classes defined by the PRD/TDD.

Threat Class

Lab Scenario

Primary Signal

Reconnaissance

Scapy port/fan-out scenario

Distinct destination-port/host cardinality

DDoS

hping3 SYN/UDP floods; Slowloris

Rate deviation, entropy, SYN/no-ACK, connection duration

Encrypted Malware

TLS metadata/fingerprint test data

JA3/JA3S/JA4 threat-intelligence match and rarity

DGA

DGArchive labeled domains replayed as DNS queries

Entropy/n-gram lexical score

DNS Tunnelling

dnscat2 / iodine

Query length, record type, NXDOMAIN anomalies

C2 Beaconing

Sandboxed C2 emulator

Inter-arrival regularity, jitter, coefficient of variation

Exfiltration

Controlled Scapy or iperf3 reverse-mode scenario

Outbound/inbound byte-ratio anomaly

6.1 Benign Baseline

Benign traffic is generated using:

iperf3 for sustained TCP/UDP traffic

Ostinato/TRex for realistic mixed-protocol traffic and load testing

Benign-only scenarios are required for every detector so that the evaluation process verifies both correct detection and absence of false alerts.

6.2 Ground-Truth Manifest

Every real-tool invocation must be wrapped so that the tool start/end times and scenario metadata are captured.

Example:

{
  "tool": "hping3",
  "type": "syn_flood",
  "start_ts": 1735300000,
  "end_ts": 1735300030,
  "src": "185.10.20.30",
  "dst": "10.0.0.10"
}

The manifest is stored under:

generator/manifests/wave_N_manifest.jsonl

It is the ground-truth input to the evaluation harness.

For real-tool scenarios, evaluation uses a tolerance window (currently specified as ±2 seconds) rather than relying on exact timestamp equality.

7. Data Source Provenance and Licensing

7.1 DGArchive

DGArchive provides family-labeled DGA domain samples for DGA model training/validation.

The project must record the actual access tier obtained before treating DGArchive as the primary training source:

Access tier obtained: [public sample / research-request access / other]
Date obtained: [fill in]
License/usage terms: [fill in]

Raw DGArchive domain lists must not be redistributed outside the project, committed to a public repository, or shared beyond the authorized team unless the applicable access terms explicitly permit it.

7.2 JA3/JA4 Threat Intelligence

Public JA3/JA4 blocklists, including feeds such as abuse.ch resources, are retrieved through the isolated threat-intelligence update path.

The feed manager must support refresh/hot-reload without requiring a full restart of the monitoring pipeline.

7.3 Tranco

Tranco top-1M is used as the benign-domain contrast/negative class for DGA classifier training.

8. Threat-Intelligence Update Path

Threat-intelligence retrieval is deliberately separated from the one-way monitoring path.

The update environment must be:

Logically and/or physically separate from lab-net

The only environment in the project permitted outbound internet access for threat-intelligence retrieval

Unable to initiate connections into lab-net

Unable to receive connections from lab-net

Unable to create an alternate return path to the mirror/diode ingest path

The separation ensures that threat-intelligence acquisition does not weaken the platform's one-way monitoring guarantee.

9. Safety and Acceptable Use

The following requirements are mandatory:

Real attack tools are used only for defensive research/testing in the isolated lab.

Attack-tool targets must be explicitly provisioned lab targets.

No attack tool may be pointed at a production, corporate, public-internet, or third-party target.

Isolation must be verified before the first attack-tool execution and after relevant network-topology changes.

Team members must read and acknowledge this document before using the real attack tools.

The sandboxed C2 emulator is a controlled internal generator. It must not provide real command-and-control functionality, exfiltrate real data, or communicate outside lab-net.

If isolation cannot be verified, attack traffic generation must not proceed.

This project uses real attack tooling to improve detection realism, but the tooling is intentionally constrained to non-production, isolated targets.

10. Verification Checklist

All required checks must pass before Phase 2 attack-tool testing begins.

Network Isolation

lab-net exists as a dedicated Docker network/VLAN.

lab-net has no route to production, corporate, or public-internet-reachable infrastructure.

Routing configuration has been inspected and verified.

Traffic-generation containers cannot reach the public internet.

Zeek/downstream monitoring services have no path back into lab-net.

Mirror/SPAN path is one-way from the lab toward the Zeek sensor.

Tool Isolation

hping3 is installed only inside the isolated lab environment.

Slowloris is installed only inside the isolated lab environment.

dnscat2 is installed only inside the isolated lab environment.

iodine is installed only inside the isolated lab environment.

Scapy traffic-generation scripts run only against explicit lab targets.

Tool versions are pinned/recorded in this document.

Sensor and Pipeline

Mirror/SPAN capture has been tested with a basic benign packet.

Zeek receives the mirrored packet.

conn.log contains the expected test flow.

Required protocol logs (conn.log, dns.log, ssl.log/TLS metadata) are available for applicable scenarios.

sensor_id is attached to downstream records.

Threat Intelligence

Threat-intelligence update path is separate from lab-net.

No shared route exists between the update path and lab-net.

DGArchive access tier is recorded in §7.1.

DGArchive license/usage restrictions are recorded.

JA3/JA4 feed refresh path is isolated from the ingest path.

Team Acknowledgment

Every team member using attack tools has read this document.

Every team member understands that the tools may cause real disruption outside the lab.

Acceptable-use requirements have been confirmed for the organization's/event's environment.

Do not begin attack-tool execution until all applicable checks pass.

This checklist must be repeated whenever the network topology, host environment, container networking, or team/developer environment changes.

11. Incident Procedure: Accidental Misconfiguration

If lab-net is found to have an unintended route to a non-lab network:

Immediately stop all attack-tool traffic generation.

Disconnect, disable, or correct the unintended network path.

Preserve relevant configuration/output needed to understand the misconfiguration.

Re-run the complete verification checklist in §10.

Do not resume attack-tool traffic until isolation is verified again.

Record the incident, root cause, corrective action, and verification result for team awareness.

If an attack tool may have transmitted outside the intended lab boundary, treat the event as a security incident and follow the organization's applicable incident-response procedure.

12. Relationship to the Detection Pipeline

The lab environment feeds the same logical detection path used by the project:

Traffic Generator / Test Target
          │
          ▼
    Mirror / SPAN
          │
          ▼
       Zeek
          │
          ▼
     Ingest Adapter
          │
          ▼
        Kafka
          │
          ▼
 Feature Extraction
          │
          ▼
 Detection Services
          │
          ▼
       Alerts
          │
          ├──► TimescaleDB
          │
          └──► API / WebSocket
                    │
                    ▼
             SOC Dashboard

No component downstream of the sensor is permitted to initiate traffic back toward the traffic source.

This preserves the central architectural guarantee of the project: passive, one-way observation only.

13. Environment Exit Conditions

The lab environment is considered ready for attack-tool testing only when:

lab-net has been verified to have no route to non-lab infrastructure.

Attack tools are confined to isolated containers/VMs.

Mirror/SPAN capture into Zeek is confirmed.

Zeek produces the expected flow/protocol records.

Threat-intelligence retrieval is isolated from the ingest path.

DGArchive access and licensing information is recorded.

Team acknowledgment is complete.

The Phase 0 exit condition is therefore a verified isolation state plus confirmed mirror capture, not merely successful container startup.

14. Change Log

Version

Date

Change

1.0

[previous date]

Initial lab environment and traffic-generation safety document

1.1

2026-08-29

Updated to align with PRD v1.1, TDD v1.1, build plan, six-detector architecture, ground-truth manifests, DGArchive/JA3/JA4 threat-intelligence path, Windows + WSL2 + Docker Desktop development workflow, and expanded verification/incident procedures

15. Final Safety Statement

Real attack traffic is permitted only inside the isolated lab environment described here.

The absence of a route from lab-net to real infrastructure must be technically verified before attack-tool execution. The monitoring pipeline itself must remain passive and must never establish a return path toward the traffic source, monitored hosts, or diode/mirror boundary.