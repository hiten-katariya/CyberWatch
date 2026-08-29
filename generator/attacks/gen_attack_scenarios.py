import time
import json
import uuid
from pathlib import Path

LOG_DIR = Path("./sensor/logs")

def append_zeek_conn(lines):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    conn_file = LOG_DIR / "conn.log"
    header = "#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\tduration\torig_bytes\tresp_bytes\n"
    if not conn_file.exists() or conn_file.stat().st_size == 0:
        with open(conn_file, "w") as f:
            f.write(header)
    with open(conn_file, "a") as f:
        for l in lines:
            f.write(l + "\n")

def append_zeek_dns(lines):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    dns_file = LOG_DIR / "dns.log"
    header = "#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\tquery\tqtype_name\trcode_name\n"
    if not dns_file.exists() or dns_file.stat().st_size == 0:
        with open(dns_file, "w") as f:
            f.write(header)
    with open(dns_file, "a") as f:
        for l in lines:
            f.write(l + "\n")

def append_zeek_tls(lines):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tls_file = LOG_DIR / "ssl.log"
    header = "#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tversion\tcipher\tserver_name\tja3\n"
    if not tls_file.exists() or tls_file.stat().st_size == 0:
        with open(tls_file, "w") as f:
            f.write(header)
    with open(tls_file, "a") as f:
        for l in lines:
            f.write(l + "\n")

def generate_recon_scenario():
    print("[+] Generating Recon Port Sweep Scenario...")
    now = time.time()
    lines = []
    for port in range(1000, 1025):
        lines.append(f"{now}\tC_RECON_{port}\t10.0.0.99\t{12000+port}\t10.0.0.100\t{port}\ttcp\t-\t0.05\t40\t0")
    append_zeek_conn(lines)

def generate_ddos_syn_scenario():
    print("[+] Generating DDoS Volumetric SYN Flood Scenario...")
    now = time.time()
    lines = []
    for i in range(120):
        lines.append(f"{now}\tC_SYN_{i}\t192.168.1.{i%50+1}\t{30000+i}\t10.0.0.200\t80\ttcp\t-\t0.01\t60\t0")
    append_zeek_conn(lines)

def generate_ddos_slowloris_scenario():
    print("[+] Generating DDoS Slowloris Scenario...")
    now = time.time()
    line = f"{now}\tC_SLOW_1\t10.0.0.88\t45000\t10.0.0.200\t80\ttcp\t-\t350.0\t150\t50"
    append_zeek_conn([line])

def generate_dga_scenario():
    print("[+] Generating DGA Domain Query Scenario...")
    now = time.time()
    lines = [
        f"{now}\tD_DGA_1\t10.0.0.50\t53001\t8.8.8.8\t53\tudp\tdns\txj89qzk2mvwp910a74bc312z.biz\tA\tNOERROR",
        f"{now}\tD_DGA_2\t10.0.0.50\t53002\t8.8.8.8\t53\tudp\tdns\tqlms902zkba9173c48n120pl.info\tA\tNXDOMAIN"
    ]
    append_zeek_dns(lines)

def generate_dns_tunnel_scenario():
    print("[+] Generating DNS Tunnelling (dnscat2/iodine) Scenario...")
    now = time.time()
    lines = [
        f"{now}\tD_TUN_1\t10.0.0.60\t53010\t8.8.8.8\t53\tudp\tdns\t0123456789abcdef0123456789abcdef0123456789abcdef.tunnel.attacker.com\tTXT\tNOERROR",
        f"{now}\tD_TUN_2\t10.0.0.60\t53011\t8.8.8.8\t53\tudp\tdns\t000000112233445566778899aabbccddeeff.tunnel.attacker.com\tNULL\tNOERROR"
    ]
    append_zeek_dns(lines)

def generate_c2_beacon_scenario():
    print("[+] Generating C2 Periodic Beacon Scenario...")
    now = time.time()
    lines = []
    # Generate 6 periodic connections 10.0s apart
    for i in range(6):
        lines.append(f"{now + (i * 10.0)}\tC_C2_{i}\t10.0.0.75\t44444\t198.51.100.5\t443\ttcp\t-\t0.5\t200\t500")
    append_zeek_conn(lines)

def generate_encrypted_malware_scenario():
    print("[+] Generating Encrypted Malware TLS Scenario...")
    now = time.time()
    lines = [
        f"{now}\tS_MAL_1\t10.0.0.80\t54321\t203.0.113.50\t443\tTLSv12\tTLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256\tmalicious-c2.internal\te7d705a3286e19ea42f587b344ee6865"
    ]
    append_zeek_tls(lines)

def generate_exfiltration_scenario():
    print("[+] Generating Bulk Exfiltration Scenario...")
    now = time.time()
    line = f"{now}\tC_EXFIL_1\t10.0.0.90\t58888\t198.51.100.99\t443\ttcp\t-\t120.0\t5000000\t10000"
    append_zeek_conn([line])

def run_all_attack_scenarios():
    print("[+] Generating Lab Attack Scenarios for all 7 Threat Classes...")
    generate_recon_scenario()
    generate_ddos_syn_scenario()
    generate_ddos_slowloris_scenario()
    generate_dga_scenario()
    generate_dns_tunnel_scenario()
    generate_c2_beacon_scenario()
    generate_encrypted_malware_scenario()
    generate_exfiltration_scenario()
    print("[+] All Lab Attack Scenarios generated successfully.")

if __name__ == "__main__":
    run_all_attack_scenarios()
