import asyncio
import websockets
import json
import requests
import time
from generator.attacks.gen_attack_scenarios import generate_recon_scenario

async def verify_live_ws_trigger():
    uri = "ws://localhost:8000/ws/alerts"
    print(f"[+] Connecting to WebSocket {uri}...")
    async with websockets.connect(uri) as ws:
        print("[+] Connected to WebSocket. Triggering Recon scenario...")
        generate_recon_scenario()
        
        # Listen for broadcast message
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            alert = json.loads(msg)
            print(f"[+] Received Live WebSocket Alert! ID: {alert.get('alert_id')}, Class: {alert.get('threat_class')}")
            assert alert.get("threat_class") in ("recon", "ddos", "dga", "dns_tunnel", "encrypted_malware", "exfiltration", "c2_beacon", "test")
            return True
        except asyncio.TimeoutError:
            print("[!] Timeout waiting for WebSocket alert.")
            return False

if __name__ == "__main__":
    asyncio.run(verify_live_ws_trigger())
