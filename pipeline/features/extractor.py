import os
import sys
import time
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("feature-extractor")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

class FeatureStateTracker:
    def __init__(self):
        # src_ip -> deque of (timestamp, dst_ip, dst_port, proto, duration, orig_bytes, resp_bytes)
        self.conn_history = defaultdict(lambda: deque(maxlen=5000))
        # (src_ip, dst_ip) -> deque of timestamp
        self.beacon_history = defaultdict(lambda: deque(maxlen=200))

    def add_conn_event(self, event):
        src_ip = event.get("src_ip", "0.0.0.0")
        dst_ip = event.get("dst_ip", "0.0.0.0")
        dst_port = event.get("dst_port", 0)
        proto = event.get("proto", "tcp")
        duration = float(event.get("duration", 0.0))
        orig_bytes = int(event.get("orig_bytes", 0))
        resp_bytes = int(event.get("resp_bytes", 0))
        now = time.time()

        self.conn_history[src_ip].append((now, dst_ip, dst_port, proto, duration, orig_bytes, resp_bytes))
        self.beacon_history[(src_ip, dst_ip)].append(now)

    def compute_conn_features(self, src_ip, dst_ip=None, window_sec=60):
        now = time.time()
        cutoff = now - window_sec

        # Filter window history
        window_events = [e for e in self.conn_history[src_ip] if e[0] >= cutoff]
        
        dst_ports = set(e[2] for e in window_events)
        dst_hosts = set(e[1] for e in window_events)
        total_orig_bytes = sum(e[5] for e in window_events)
        total_resp_bytes = sum(e[6] for e in window_events)
        flow_count = len(window_events)

        byte_ratio = (total_orig_bytes / total_resp_bytes) if total_resp_bytes > 0 else float(total_orig_bytes or 0)
        pps = flow_count / window_sec if window_sec > 0 else 0

        # Beacon inter-arrival calculation
        inter_arrivals = []
        if dst_ip and (src_ip, dst_ip) in self.beacon_history:
            timestamps = [t for t in self.beacon_history[(src_ip, dst_ip)] if t >= now - 3600]
            if len(timestamps) >= 3:
                for i in range(1, len(timestamps)):
                    inter_arrivals.append(timestamps[i] - timestamps[i-1])

        return {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "window_sec": window_sec,
            "flow_count": flow_count,
            "pps": pps,
            "unique_dst_ports": len(dst_ports),
            "unique_dst_hosts": len(dst_hosts),
            "total_orig_bytes": total_orig_bytes,
            "total_resp_bytes": total_resp_bytes,
            "byte_ratio": byte_ratio,
            "inter_arrivals": inter_arrivals
        }

def run_feature_extractor():
    logger.info("Initializing Shared Feature Extractor Service...")
    state = FeatureStateTracker()

    consumer = None
    for attempt in range(1, 15):
        try:
            logger.info(f"Connecting Consumer to {KAFKA_BROKER}...")
            consumer = KafkaConsumer(
                "events.conn", "events.dns", "events.tls",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='feature-extractor-group'
            )
            logger.info("Kafka consumer connected.")
            break
        except Exception as e:
            logger.warning(f"Consumer connection attempt failed: {e}. Retrying in 2s...")
            time.sleep(2)

    producer = None
    for attempt in range(1, 15):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            logger.info("Kafka producer connected.")
            break
        except Exception as e:
            logger.warning(f"Producer connection attempt failed: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer or not producer:
        logger.error("Failed to connect Kafka components. Exiting.")
        sys.exit(1)

    try:
        for msg in consumer:
            topic = msg.topic
            event = msg.value

            if topic == "events.conn":
                state.add_conn_event(event)
                src_ip = event.get("src_ip", "0.0.0.0")
                dst_ip = event.get("dst_ip", "0.0.0.0")
                
                # Compute 10s and 60s window features
                features_10s = state.compute_conn_features(src_ip, dst_ip, window_sec=10)
                features_60s = state.compute_conn_features(src_ip, dst_ip, window_sec=60)
                
                feature_record = {
                    "sensor_id": event.get("sensor_id", SENSOR_ID),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "raw_event": event,
                    "features_10s": features_10s,
                    "features_60s": features_60s
                }
                producer.send("features.conn", feature_record)
            
            elif topic == "events.dns":
                producer.send("features.dns", event)
            elif topic == "events.tls":
                producer.send("features.tls", event)

            producer.flush()
    except KeyboardInterrupt:
        logger.info("Shutting down feature extractor.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_feature_extractor()
