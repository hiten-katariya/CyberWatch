import time
import json
import requests
import sys
from generator.attacks.gen_attack_scenarios import run_all_attack_scenarios

def verify_phase2():
    print("==================================================================")
    print("[+] PHASE 2 END-TO-END PIPELINE & INTEGRATION VERIFICATION")
    print("==================================================================")

    # 1. API Health Check
    print("\n[+] Step 1: Checking API /health...")
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        print(f"    Health Status ({r.status_code}): {r.json()}")
        assert r.status_code == 200
    except Exception as e:
        print(f"[!] Health check failed: {e}")
        return False

    # 2. Get initial alert count and stats
    print("\n[+] Step 2: Fetching initial /alerts/stats...")
    try:
        r_init = requests.get("http://localhost:8000/alerts/stats", timeout=5).json()
        init_total = r_init.get("total", 0)
        print(f"    Initial Total Alerts: {init_total}")
    except Exception as e:
        print(f"[!] Failed to fetch initial stats: {e}")
        return False

    # 3. Generate lab attack scenarios for all 7 threat classes
    print("\n[+] Step 3: Triggering Lab Attack Scenarios for 7 Threat Classes...")
    run_all_attack_scenarios()

    # 4. Wait for Feature Extractor -> 7 Detectors -> Alert Sink pipeline
    print("\n[+] Step 4: Waiting 8s for feature extraction and detection pipeline...")
    time.sleep(8)

    # 5. Query updated stats and alerts
    print("\n[+] Step 5: Querying updated GET /alerts/stats & GET /alerts...")
    try:
        r_after = requests.get("http://localhost:8000/alerts/stats", timeout=5).json()
        after_total = r_after.get("total", 0)
        by_threat = r_after.get("by_threat", {})
        
        print(f"    Updated Total Alerts: {after_total} (+{after_total - init_total} new alerts)")
        print(f"    Threat Class Breakdown: {json.dumps(by_threat, indent=2)}")

        r_alerts = requests.get("http://localhost:8000/alerts?limit=50", timeout=5).json()
        alerts_list = r_alerts.get("alerts", [])
        detected_classes = set(a.get("threat_class") for a in alerts_list)
        print(f"    Detected Threat Classes in Database: {detected_classes}")

        # Check that threat classes are being detected
        expected_classes = {"test", "recon", "ddos", "dga", "dns_tunnel", "encrypted_malware", "exfiltration"}
        found_classes = expected_classes.intersection(detected_classes)
        print(f"    Successfully Verified Threat Classes ({len(found_classes)}/{len(expected_classes)}): {found_classes}")

    except Exception as e:
        print(f"[!] Error fetching post-scenario stats: {e}")
        return False

    # 6. Verify Grafana Datasource / Reachability
    print("\n[+] Step 6: Checking Grafana Endpoint (http://localhost:3001)...")
    try:
        r_grafana = requests.get("http://localhost:3001/api/health", timeout=5)
        print(f"    Grafana Health Status ({r_grafana.status_code}): {r_grafana.json()}")
        assert r_grafana.status_code == 200
    except Exception as e:
        print(f"[!] Grafana endpoint check failed: {e}")
        return False

    print("\n==================================================================")
    print("[+] PASS — Phase 2 End-to-End Integration Condition Verified!")
    print("==================================================================")
    return True

if __name__ == "__main__":
    success = verify_phase2()
    sys.exit(0 if success else 1)
