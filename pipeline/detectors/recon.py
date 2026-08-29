import os
import sys
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
from pipeline.detectors.config_loader import load_detector_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("recon-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def run_recon_detector():
    logger.info("Initializing Reconnaissance Threat Detector...")
    cfg = load_detector_config().get("recon", {})
    port_threshold = cfg.get("dst_port_fanout_threshold", 15)
    host_threshold = cfg.get("dst_host_fanout_threshold", 10)
    window_sec = cfg.get("window_seconds", 10)
    severity = cfg.get("severity", "medium")
    confidence = float(cfg.get("confidence", 0.90))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "features.conn",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='recon-detector-group'
            )
            logger.info("Kafka consumer connected to 'features.conn'.")
            break
        except Exception as e:
            logger.warning(f"Consumer error: {e}. Retrying in 2s...")
            time.sleep(2)

    producer = None
    for attempt in range(1, 15):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            logger.info("Kafka producer connected to 'alerts'.")
            break
        except Exception as e:
            logger.warning(f"Producer error: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer or not producer:
        sys.exit(1)

    try:
        for msg in consumer:
            feat_record = msg.value
            raw_event = feat_record.get("raw_event", {})
            f10 = feat_record.get("features_10s", {})
            
            unique_ports = f10.get("unique_dst_ports", 0)
            unique_hosts = f10.get("unique_dst_hosts", 0)

            if unique_ports >= port_threshold or unique_hosts >= host_threshold:
                pattern = "port_fanout" if unique_ports >= port_threshold else "host_fanout"
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": raw_event.get("sensor_id", SENSOR_ID),
                    "threat_class": "recon",
                    "severity": severity,
                    "confidence": confidence,
                    "flow_identifier": {
                        "src_ip": raw_event.get("src_ip", "0.0.0.0"),
                        "dst_ip": raw_event.get("dst_ip", "0.0.0.0"),
                        "src_port": raw_event.get("src_port", 0),
                        "dst_port": raw_event.get("dst_port", 0),
                        "proto": raw_event.get("proto", "tcp")
                    },
                    "evidence": {
                        "unique_dst_ports": unique_ports,
                        "unique_dst_hosts": unique_hosts,
                        "window_seconds": window_sec,
                        "threshold": port_threshold,
                        "pattern": pattern
                    }
                }
                logger.info(f"Recon Alert Fired: {alert['alert_id']} ({pattern})")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping recon detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_recon_detector()
