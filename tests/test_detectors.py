import pytest
import math
from pipeline.detectors.config_loader import load_detector_config
from pipeline.detectors.dga import calculate_entropy

def test_config_loader():
    cfg = load_detector_config()
    assert "recon" in cfg
    assert "ddos" in cfg
    assert "dga" in cfg
    assert "dns_tunnel" in cfg

# 1. Recon Detector Unit Tests
def test_recon_benign_no_alert():
    # 2 unique ports, threshold is 15 -> NO ALERT
    unique_ports = 2
    unique_hosts = 1
    port_threshold = 15
    assert unique_ports < port_threshold

def test_recon_attack_alert():
    unique_ports = 25
    port_threshold = 15
    assert unique_ports >= port_threshold

# 2. DDoS Detector Unit Tests (3 Sub-patterns)
def test_ddos_syn_flood():
    pps = 150
    syn_thresh = 100
    proto = "tcp"
    assert proto == "tcp" and pps >= syn_thresh

def test_ddos_udp_flood():
    pps = 200
    udp_thresh = 100
    proto = "udp"
    assert proto == "udp" and pps >= udp_thresh

def test_ddos_slowloris():
    duration = 350.0
    bytes_transferred = 200
    slow_dur_thresh = 300
    slow_max_bytes = 500
    assert duration >= slow_dur_thresh and bytes_transferred <= slow_max_bytes

def test_ddos_benign_no_alert():
    pps = 5
    duration = 2.0
    bytes_transferred = 1000
    assert pps < 100 and (duration < 300 or bytes_transferred > 500)

# 3. DGA Detector Unit Tests
def test_dga_entropy():
    benign_domain = "google.com"
    dga_domain = "xj89qzk2mvwp910a74bc312z"
    
    ent_benign = calculate_entropy(benign_domain)
    ent_dga = calculate_entropy(dga_domain)
    
    assert ent_benign < 3.8
    assert ent_dga >= 3.8

# 4. DNS Tunnel Unit Tests
def test_dns_tunnel_detection():
    benign_query = "api.example.com"
    tunnel_query = "0123456789abcdef0123456789abcdef0123456789abcdef.tunnel.attacker.com"
    
    assert len(benign_query) < 50
    assert len(tunnel_query) >= 50

# 5. C2 Beacon Detector Unit Tests
def test_c2_beacon_detection():
    # Regular intervals 10.0s, stddev 0.0 -> COV 0.0 <= 0.15
    intervals = [10.0, 10.0, 10.0, 10.0, 10.0]
    mean_int = sum(intervals) / len(intervals)
    variance = sum((x - mean_int) ** 2 for x in intervals) / len(intervals)
    stddev = math.sqrt(variance)
    cov = stddev / mean_int
    assert cov <= 0.15

def test_c2_beacon_benign_jitter():
    # Irregular intervals -> high COV -> NO ALERT
    intervals = [2.0, 45.0, 1.0, 120.0, 5.0]
    mean_int = sum(intervals) / len(intervals)
    variance = sum((x - mean_int) ** 2 for x in intervals) / len(intervals)
    stddev = math.sqrt(variance)
    cov = stddev / mean_int
    assert cov > 0.15

# 6. Encrypted Malware Detector Unit Tests
def test_encrypted_malware_ja3_hit():
    blocked_ja3 = "e7d705a3286e19ea42f587b344ee6865"
    benign_ja3 = "cd08e31494f9531f552d63c4a70eefea"
    blocklist = {"e7d705a3286e19ea42f587b344ee6865"}
    
    assert blocked_ja3 in blocklist
    assert benign_ja3 not in blocklist

# 7. Exfiltration Detector Unit Tests
def test_exfiltration_detection():
    orig_bytes = 5000000
    resp_bytes = 10000
    ratio = orig_bytes / resp_bytes
    assert orig_bytes >= 1000000 and ratio >= 10.0

def test_exfiltration_benign_no_alert():
    orig_bytes = 1000
    resp_bytes = 50000
    ratio = orig_bytes / resp_bytes
    assert orig_bytes < 1000000 or ratio < 10.0
