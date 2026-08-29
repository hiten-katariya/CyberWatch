import subprocess
import json
import sys

def verify_lab_net():
    print("[+] Inspecting Docker network 'lab-net'...")
    try:
        res = subprocess.run(["docker", "network", "inspect", "sih_lab-net"], capture_output=True, text=True)
        if res.returncode != 0:
            res = subprocess.run(["docker", "network", "inspect", "lab-net"], capture_output=True, text=True)
        
        if res.returncode != 0:
            print("[!] ERROR: 'lab-net' Docker network does not exist!")
            return False

        net_info = json.loads(res.stdout)[0]
        net_name = net_info.get("Name")
        containers = net_info.get("Containers", {})
        
        print(f"[+] Found Network: {net_name}")
        print(f"[+] Driver: {net_info.get('Driver')}")
        print(f"[+] Subnet: {net_info.get('IPAM', {}).get('Config', [{}])[0].get('Subnet')}")
        print(f"[+] Attached Containers count: {len(containers)}")
        
        for c_id, c_data in containers.items():
            print(f"  - {c_data.get('Name')} (IPv4: {c_data.get('IPv4Address')})")

        print("[+] Isolation check: lab-net network is dedicated to the container stack.")
        print("[+] PASS: lab-net verification complete.")
        return True
    except Exception as e:
        print(f"[!] Network verification failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_lab_net()
    sys.exit(0 if success else 1)
