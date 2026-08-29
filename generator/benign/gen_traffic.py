import socket
import time
import argparse
import sys

def run_benign_generator(target_host="127.0.0.1", port=5201, duration=60):
    print(f"[+] Generating TCP/UDP benign traffic towards {target_host}:{port} for {duration}s...")
    end_time = time.time() + duration
    
    # Simple TCP echo server in daemon thread if target is localhost
    if target_host in ("127.0.0.1", "localhost"):
        import threading
        def dummy_server():
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", port))
                server.listen(5)
                server.settimeout(1.0)
                while time.time() < end_time + 2:
                    try:
                        conn, _ = server.accept()
                        conn.recv(1024)
                        conn.close()
                    except socket.timeout:
                        continue
                server.close()
            except Exception as e:
                pass
        t = threading.Thread(target=dummy_server, daemon=True)
        t.start()
        time.sleep(0.5)

    packets_sent = 0
    while time.time() < end_time:
        try:
            # Send TCP session
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((target_host, port))
            sock.sendall(b"BENIGN_PHASE1_TEST_DATA_" + b"X" * 100)
            sock.close()
            packets_sent += 1

            # Send UDP session
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.sendto(b"BENIGN_UDP_TEST_DATA", (target_host, port))
            udp_sock.close()
            packets_sent += 1
        except Exception as e:
            pass
        time.sleep(0.5)

    print(f"[+] Benign generator finished. Sent ~{packets_sent} packets/flows.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 Benign Traffic Generator")
    parser.add_argument("--host", default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, default=5201, help="Target port")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    args = parser.parse_args()
    run_benign_generator(args.host, args.port, args.duration)
