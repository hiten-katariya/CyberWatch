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
logger = logging.getLogger("ddos-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def run_ddos_detector():
    logger.info("Initializing DDoS Threat Detector...")
    cfg = load_detector_config().get("ddos", {})
    syn_pps_thresh = cfg.get("volumetric_syn_threshold_pps", 100)
    udp_pps_thresh = cfg.get("volumetric_udp_threshold_pps", 100)
    slow_dur_thresh = cfg.get("slow_exhaustion_duration_min", 300)
    slow_max_bytes = cfg.get("slow_exhaustion_max_bytes", 500)
    severity = cfg.get("severity", "critical")
    confidence = float(cfg.get("confidence", 0.95))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "features.conn",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='ddos-detector-group'
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
            f10 = feat_record.get("features_10s", {})

            proto = raw.get("proto", "tcp").lower()
            duration = float(raw.get("duration", 0.0))
            orig_bytes = int(raw.get("orig_bytes", 0))
            resp_bytes = int(raw.get("resp_bytes", 0))
            total_bytes = orig_bytes + resp_bytes
            pps = f10.get("pps", 0)

            pattern = None
            evidence_details = {}

            # Check 1: Volumetric SYN flood
            if proto == "tcp" and pps >= syn_pps_thresh:
                pattern = "volumetric_syn"
                evidence_details = {"pps": pps, "threshold_pps": syn_pps_thresh}

            # Check 2: Volumetric UDP flood
            elif proto == "udp" and pps >= udp_pps_thresh:
                pattern = "volumetric_udp"
                evidence_details = {"pps": pps, "threshold_pps": udp_pps_thresh}

            # Check 3: Slowloris connection exhaustion
            elif proto == "tcp" and duration >= slow_dur_thresh and total_bytes <= slow_max_bytes:
                pattern = "slow_exhaustion"
                evidence_details = {
                    "duration_sec": duration,
                    "total_bytes": total_bytes,
                    "max_bytes_allowed": slow_max_bytes
                }

            if pattern:
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": raw.get("sensor_id", SENSOR_ID),
                    "threat_class": "ddos",
                    "severity": severity,
                    "confidence": confidence,
                    "flow_identifier": {
                        "src_ip": raw.get("src_ip", "0.0.0.0"),
                        "dst_ip": raw.get("dst_ip", "0.0.0.0"),
                        "src_port": raw.get("src_port", 0),
                        "dst_port": raw.get("dst_port", 0),
                        "proto": proto
                    },
                    "evidence": {
                        "pattern": pattern,
                        **evidence_details
                    }
                }
                logger.info(f"DDoS Alert Fired: {alert['alert_id']} ({pattern})")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping DDoS detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_ddos_detector()
