import os
import sys
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
try:
    from pipeline.detectors.config_loader import load_detector_config
except ModuleNotFoundError:
    from config_loader import load_detector_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("exfiltration-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def run_exfiltration_detector():
    logger.info("Initializing Exfiltration Threat Detector...")
    cfg = load_detector_config().get("exfiltration", {})
    ratio_threshold = cfg.get("byte_ratio_threshold", 10.0)
    min_bytes = cfg.get("min_outbound_bytes", 1000000)
    window_sec = cfg.get("window_seconds", 60)
    severity = cfg.get("severity", "high")
    confidence = float(cfg.get("confidence", 0.89))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "features.conn",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='exfiltration-detector-group'
            )
            logger.info("Kafka consumer connected to 'features.conn'.")
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
            feat_record = msg.value
            raw = feat_record.get("raw_event", {})
            f60 = feat_record.get("features_60s", {})
            
            orig_bytes = f60.get("total_orig_bytes", int(raw.get("orig_bytes", 0)))
            resp_bytes = f60.get("total_resp_bytes", int(raw.get("resp_bytes", 0)))
            ratio = f60.get("byte_ratio", (orig_bytes / resp_bytes) if resp_bytes > 0 else float(orig_bytes))

            if orig_bytes >= min_bytes and ratio >= ratio_threshold:
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": raw.get("sensor_id", SENSOR_ID),
                    "threat_class": "exfiltration",
                    "severity": severity,
                    "confidence": confidence,
                    "flow_identifier": {
                        "src_ip": raw.get("src_ip", "0.0.0.0"),
                        "dst_ip": raw.get("dst_ip", "0.0.0.0"),
                        "src_port": raw.get("src_port", 0),
                        "dst_port": raw.get("dst_port", 0),
                        "proto": raw.get("proto", "tcp")
                    },
                    "evidence": {
                        "outbound_bytes": orig_bytes,
                        "inbound_bytes": resp_bytes,
                        "byte_ratio": round(ratio, 2),
                        "ratio_threshold": ratio_threshold,
                        "pattern": "bulk_outbound_transfer"
                    }
                }
                logger.info(f"Exfiltration Alert Fired: {alert['alert_id']} (outbound: {orig_bytes} bytes, ratio: {ratio:.1f})")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping exfiltration detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_exfiltration_detector()
