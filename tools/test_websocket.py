import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/alerts"
    print(f"[+] Connecting to WebSocket {uri}...")
    async with websockets.connect(uri) as websocket:
        print("[+] WebSocket connection established.")
        # Send ping message
        await websocket.send("ping")
        print("[+] Sent keepalive frame.")
        # Wait up to 2 seconds
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"[+] Received message over WebSocket: {msg}")
        except asyncio.TimeoutError:
            print("[+] WebSocket connection is active and listening for live alerts.")

if __name__ == "__main__":
    asyncio.run(test_ws())
