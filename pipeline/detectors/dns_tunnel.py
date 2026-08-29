import os
import sys
import time
import json
import math
import uuid
import logging
from collections import Counter
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
try:
    from pipeline.detectors.config_loader import load_detector_config
except ModuleNotFoundError:
    from config_loader import load_detector_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("dns-tunnel-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def calculate_entropy(s):
    if not s: return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((cnt / length) * math.log2(cnt / length) for cnt in counts.values())

def run_dns_tunnel_detector():
    logger.info("Initializing DNS Tunnelling Threat Detector...")
    cfg = load_detector_config().get("dns_tunnel", {})
    query_len_threshold = cfg.get("query_length_threshold", 50)
    label_len_threshold = cfg.get("label_length_threshold", 30)
    entropy_thresh = cfg.get("query_entropy_threshold", 3.9)
    suspicious_types = cfg.get("suspicious_qtypes", ["TXT", "NULL", "ANY"])
    severity = cfg.get("severity", "high")
    confidence = float(cfg.get("confidence", 0.92))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "events.dns",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='dns-tunnel-detector-group'
            )
            logger.info("Kafka consumer connected to 'events.dns'.")
            break
        except Exception as e:
            logger.warning(f"Consumer connection error: {e}. Retrying in 2s...")
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
            logger.warning(f"Producer connection error: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer or not producer:
        sys.exit(1)

    try:
        for msg in consumer:
            event = msg.value
            query = event.get("query", "")
            qtype = str(event.get("qtype_name", "")).upper()
            if not query:
                continue

            query_len = len(query)
            labels = query.split(".")
            max_label_len = max(len(lbl) for lbl in labels) if labels else 0
            ent = calculate_entropy(query)

            is_tunnel = False
            pattern = "dns_tunnel_anomaly"

            if query_len >= query_len_threshold:
                is_tunnel = True
                pattern = "high_query_length"
            elif max_label_len >= label_len_threshold:
                is_tunnel = True
                pattern = "high_label_length"
            elif qtype in suspicious_types and (query_len >= 35 or ent >= entropy_thresh):
                is_tunnel = True
                pattern = f"suspicious_record_type_{qtype}"

            if is_tunnel:
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": event.get("sensor_id", SENSOR_ID),
                    "threat_class": "dns_tunnel",
                    "severity": severity,
                    "confidence": confidence,
                    "flow_identifier": {
                        "src_ip": event.get("src_ip", "0.0.0.0"),
                        "dst_ip": event.get("dst_ip", "0.0.0.0"),
                        "src_port": event.get("src_port", 0),
                        "dst_port": event.get("dst_port", 53),
                        "proto": "udp"
                    },
                    "evidence": {
                        "query": query,
                        "query_length": query_len,
                        "max_label_length": max_label_len,
                        "entropy": round(ent, 3),
                        "qtype_name": qtype,
                        "pattern": pattern
                    }
                }
                logger.info(f"DNS Tunnel Alert Fired: {alert['alert_id']} ({pattern})")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping DNS tunnel detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_dns_tunnel_detector()
