import os
import sys
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("placeholder-detector")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_CONN = os.getenv("KAFKA_TOPIC_CONN", "events.conn")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")

def run_placeholder_detector():
    logger.info("Initializing Phase 1 Placeholder Detector")

    # Connect Consumer
    consumer = None
    for attempt in range(1, 15):
        try:
            logger.info(f"Connecting Consumer to {KAFKA_BROKER} (Attempt {attempt})...")
            consumer = KafkaConsumer(
                KAFKA_TOPIC_CONN,
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='placeholder-detector-group'
            )
            logger.info("Consumer connected successfully.")
            break
        except Exception as e:
            logger.warning(f"Consumer connection attempt failed: {e}. Retrying in 2s...")
            time.sleep(2)

    # Connect Producer
    producer = None
    for attempt in range(1, 15):
        try:
            logger.info(f"Connecting Producer to {KAFKA_BROKER} (Attempt {attempt})...")
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            logger.info("Producer connected successfully.")
            break
        except Exception as e:
            logger.warning(f"Producer connection attempt failed: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer or not producer:
        logger.error("Failed to connect Kafka components. Exiting.")
        sys.exit(1)

    alert_fired = False
    logger.info(f"Waiting for first valid event on topic '{KAFKA_TOPIC_CONN}'...")

    try:
        for msg in consumer:
            event = msg.value
            logger.info(f"Received event from '{KAFKA_TOPIC_CONN}': {event}")
            
            if not alert_fired:
                alert = {
                    "schema_version": "1.0",
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_id": event.get("sensor_id", SENSOR_ID),
                    "threat_class": "test",
                    "severity": "low",
                    "confidence": 1.0,
                    "flow_identifier": {
                        "src_ip": event.get("src_ip", "10.0.0.2"),
                        "dst_ip": event.get("dst_ip", "10.0.0.3"),
                        "src_port": event.get("src_port", 1234),
                        "dst_port": event.get("dst_port", 5201),
                        "proto": event.get("proto", "tcp")
                    },
                    "evidence": {
                        "type": "phase1_placeholder",
                        "message": "Phase 1 pipeline verification alert"
                    }
                }

                logger.info(f"Generating Phase 1 Placeholder Alert: {alert['alert_id']}")
                producer.send(KAFKA_TOPIC_ALERTS, alert)
                producer.flush()
                alert_fired = True
                logger.info("Successfully published placeholder alert to topic 'alerts'. Standing by.")
            else:
                logger.info("Subsequent event received — placeholder detector fired already. Skipping.")

    except KeyboardInterrupt:
        logger.info("Shutting down placeholder detector.")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    run_placeholder_detector()
