# Threat Detection Signals & Feature Specification

## Phase 2 Detector Specifications

### 1. Reconnaissance (`recon`)
- **Signal**: Rapid scanning across multiple destination ports or target hosts from a single source IP.
- **Features Used**: `unique_dst_ports`, `unique_dst_hosts`, `window_seconds`.
- **Threshold**: Centrally configured in `config/detectors.yaml` (`dst_port_fanout_threshold: 15`, `dst_host_fanout_threshold: 10`).

### 2. DDoS (`ddos`)
- **Signal**: Volumetric packet floods or slow connection state exhaustion.
- **Sub-patterns**:
  - `volumetric_syn`: High TCP SYN packet rate.
  - `volumetric_udp`: High UDP packet rate.
  - `slow_exhaustion`: Low byte transfer over long connection duration (Slowloris).
- **Features Used**: `pps`, `duration`, `total_bytes`, `proto`.

### 3. DGA (`dga`)
- **Signal**: Algorithmically generated domain queries.
- **Features Used**: Domain length, Shannon character entropy, digit ratio, n-gram lexical distribution.
- **Model Fallback**: If ML model binary is missing/unreadable, detector gracefully uses rule-based entropy (> 3.8) and length (> 22) thresholds.

### 4. DNS Tunnelling (`dns_tunnel`)
- **Signal**: Encoded data exfiltration over DNS queries.
- **Features Used**: `query_length`, `max_label_length`, `entropy`, `qtype_name` (TXT, NULL, ANY).

### 5. C2 Beaconing (`c2_beacon`)
- **Signal**: Periodic automated command-and-control heartbeats.
- **Features Used**: Inter-arrival timestamps, mean interval, standard deviation, coefficient of variation (`stddev / mean <= 0.15`).

### 6. Encrypted Malware (`encrypted_malware`)
- **Signal**: Malicious TLS handshake signatures.
- **Features Used**: `ja3` hash, `server_name`, TLS version/cipher.
- **Threat Intel**: Local JA3 hash blocklist in `config/detectors.yaml`.

### 7. Exfiltration (`exfiltration`)
- **Signal**: Unusually high outbound byte transfer to external destinations.
- **Features Used**: `total_orig_bytes`, `total_resp_bytes`, `byte_ratio` (`orig / resp >= 10.0`).
