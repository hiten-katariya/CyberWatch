import time
import json
import requests
import socket
import sys
from pathlib import Path

def test_pipeline_e2e():
    print("[+] Step 1: Checking API /health endpoint...")
    try:
        resp = requests.get("http://localhost:8000/health", timeout=5)
        print(f"[+] Health Response ({resp.status_code}): {resp.json()}")
    except Exception as e:
        print(f"[!] Health check failed: {e}")

    print("[+] Step 2: Generating Benign Traffic Sample to Zeek log...")
    log_dir = Path("./sensor/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    conn_log = log_dir / "conn.log"
    
    # Write a test Zeek conn.log line to trigger Ingest
    header = "#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\tduration\torig_bytes\tresp_bytes\n"
    line = f"{time.time()}\tC_PHASE1_TEST\t10.0.0.2\t1234\t10.0.0.3\t5201\ttcp\t-\t1.23\t1000\t2000\n"
    
    if not conn_log.exists() or conn_log.stat().st_size == 0:
        with open(conn_log, "w") as f:
            f.write(header)
            f.write(line)
    else:
        with open(conn_log, "a") as f:
            f.write(line)
            
    print(f"[+] Appended benign test flow to {conn_log}")

    print("[+] Step 3: Waiting 5s for Ingest -> Placeholder Detector -> Alert Sink pipeline...")
    time.sleep(5)

    print("[+] Step 4: Querying GET http://localhost:8000/alerts...")
    try:
        resp = requests.get("http://localhost:8000/alerts", timeout=5)
        data = resp.json()
        print(f"[+] GET /alerts Response: {json.dumps(data, indent=2)}")
        if data.get("count", 0) > 0:
            print("[+] PASS: Placeholder alert successfully retrieved from API!")
            return True
        else:
            print("[!] WARNING: Alerts count is 0. Checking again in 3s...")
            time.sleep(3)
            resp = requests.get("http://localhost:8000/alerts", timeout=5)
            data = resp.json()
            if data.get("count", 0) > 0:
                print("[+] PASS: Placeholder alert successfully retrieved from API!")
                return True
            print("[!] FAIL: Placeholder alert was not found in TimescaleDB via API.")
            return False
    except Exception as e:
        print(f"[!] Error fetching alerts from API: {e}")
        return False

if __name__ == "__main__":
    success = test_pipeline_e2e()
    sys.exit(0 if success else 1)
