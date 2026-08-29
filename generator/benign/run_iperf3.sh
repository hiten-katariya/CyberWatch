#!/bin/bash
# Phase 1 — Benign Traffic Generator using iperf3
set -e

echo "[+] Starting Phase 1 Benign Traffic Generation (iperf3)"
SERVER_IP=${1:-"127.0.0.1"}
DURATION=${2:-60}

if command -v iperf3 >/dev/null 2>&1; then
    echo "[+] Running iperf3 server..."
    iperf3 -s -D || true
    echo "[+] Running iperf3 client traffic for ${DURATION}s to ${SERVER_IP}..."
    iperf3 -c ${SERVER_IP} -t ${DURATION} -p 5201
    iperf3 -c ${SERVER_IP} -u -b 10M -t ${DURATION} -p 5201
else
    echo "[!] iperf3 not found on PATH. Falling back to Python benign traffic generator..."
    python3 generator/benign/gen_traffic.py --duration ${DURATION}
fi

echo "[+] Benign traffic generation complete."
