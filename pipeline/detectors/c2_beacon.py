import os
import sys
import time
import json
import math
import uuid
import logging
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
try:
    from pipeline.detectors.config_loader import load_detector_config
except ModuleNotFoundError:
    from config_loader import load_detector_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("c2-beacon-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def run_c2_beacon_detector():
    logger.info("Initializing C2 Beaconing Threat Detector...")
    cfg = load_detector_config().get("c2_beacon", {})
    min_count = cfg.get("min_repetition_count", 5)
    max_cov = cfg.get("max_coefficient_of_variation", 0.15)
    min_interval = cfg.get("min_mean_interval_sec", 5.0)
    max_interval = cfg.get("max_mean_interval_sec", 3600.0)
    severity = cfg.get("severity", "critical")
    confidence = float(cfg.get("confidence", 0.91))

    consumer = None
    for attempt in range(1, 15):
        try:
            consumer = KafkaConsumer(
                "features.conn",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='c2-beacon-detector-group'
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
            inter_arrivals = f60.get("inter_arrivals", [])

            if len(inter_arrivals) >= min_count - 1:
                mean_interval = sum(inter_arrivals) / len(inter_arrivals)
                if min_interval <= mean_interval <= max_interval:
                    variance = sum((x - mean_interval) ** 2 for x in inter_arrivals) / len(inter_arrivals)
                    stddev = math.sqrt(variance)
                    cov = stddev / mean_interval if mean_interval > 0 else 1.0

                    if cov <= max_cov:
                        alert = {
                            "schema_version": "1.0",
                            "alert_id": str(uuid.uuid4()),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "sensor_id": raw.get("sensor_id", SENSOR_ID),
                            "threat_class": "c2_beacon",
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
                                "mean_interval": round(mean_interval, 2),
                                "interval_stddev": round(stddev, 2),
                                "coefficient_of_variation": round(cov, 3),
                                "repetition_count": len(inter_arrivals) + 1,
                                "pattern": "periodic_beacon"
                            }
                        }
                        logger.info(f"C2 Beacon Alert Fired: {alert['alert_id']} (mean: {mean_interval:.1f}s, cov: {cov:.3f})")
                        producer.send(KAFKA_TOPIC_ALERTS, alert)
                        producer.flush()
    except KeyboardInterrupt:
        logger.info("Stopping C2 beacon detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_c2_beacon_detector()
