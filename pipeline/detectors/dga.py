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
logger = logging.getLogger("dga-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def calculate_entropy(s):
    if not s: return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((cnt / length) * math.log2(cnt / length) for cnt in counts.values())

def run_dga_detector():
    logger.info("Initializing DGA Threat Detector...")
    cfg = load_detector_config().get("dga", {})
    len_threshold = cfg.get("domain_length_threshold", 22)
    entropy_threshold = cfg.get("entropy_threshold", 3.8)
    severity = cfg.get("severity", "high")
    confidence = float(cfg.get("confidence", 0.88))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "events.dns",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='dga-detector-group'
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
            logger.warning(f"Producer error: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer or not producer:
        sys.exit(1)

    try:
        for msg in consumer:
            event = msg.value
            query = event.get("query", "")
            if not query:
                continue

            # Strip TLD if present for entropy calculation
            domain_body = query.split(".")[0] if "." in query else query
            ent = calculate_entropy(domain_body)
            length = len(domain_body)

            if length >= len_threshold or ent >= entropy_threshold:
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": event.get("sensor_id", SENSOR_ID),
                    "threat_class": "dga",
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
                        "domain_body": domain_body,
                        "entropy": round(ent, 3),
                        "entropy_threshold": entropy_threshold,
                        "length": length,
                        "length_threshold": len_threshold,
                        "pattern": "lexical_dga_entropy"
                    }
                }
                logger.info(f"DGA Alert Fired: {alert['alert_id']} (query: {query}, entropy: {ent:.2f})")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping DGA detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_dga_detector()
