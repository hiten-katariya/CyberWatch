import os
import sys
import time
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from kafka import KafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("alert-sink")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")

DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DB_NAME = os.getenv("DATABASE_NAME", "threatpipe")
DB_USER = os.getenv("DATABASE_USER", "postgres")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "threatpipe")

def get_db_connection(max_retries=15, retry_interval=2):
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to DB {DB_NAME} at {DB_HOST}:{DB_PORT} (Attempt {attempt}/{max_retries})...")
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            conn.autocommit = True
            logger.info("Successfully connected to TimescaleDB.")
            return conn
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Retrying in {retry_interval}s...")
            time.sleep(retry_interval)
    logger.error("Failed to connect to TimescaleDB after max retries.")
    return None

def init_db(conn):
    with conn.cursor() as cur:
        # Create alerts table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id UUID PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                sensor_id TEXT NOT NULL,
                threat_class TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                flow_identifier JSONB NOT NULL,
                evidence JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        # Indexes for fast querying
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_threat_class ON alerts (threat_class);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_sensor_id ON alerts (sensor_id);")
        logger.info("Database schema and indexes initialized.")

def save_alert(conn, alert):
    alert_id = alert.get("alert_id")
    timestamp = alert.get("timestamp")
    sensor_id = alert.get("sensor_id", "unknown")
    threat_class = alert.get("threat_class", "unknown")
    severity = alert.get("severity", "low")
    confidence = float(alert.get("confidence", 1.0))
    flow_identifier = alert.get("flow_identifier", {})
    evidence = alert.get("evidence", {})

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alerts (
                alert_id, timestamp, sensor_id, threat_class, severity, confidence, flow_identifier, evidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_id) DO NOTHING;
        """, (
            alert_id, timestamp, sensor_id, threat_class, severity, confidence, Json(flow_identifier), Json(evidence)
        ))
        logger.info(f"Persisted alert {alert_id} (class: {threat_class}, severity: {severity}) into TimescaleDB.")

def run_alert_sink():
    logger.info("Starting Pipeline Alert Sink")
    
    db_conn = get_db_connection()
    if not db_conn:
        sys.exit(1)
    init_db(db_conn)

    consumer = None
    for attempt in range(1, 15):
        try:
            logger.info(f"Connecting Consumer to {KAFKA_BROKER} topic '{KAFKA_TOPIC_ALERTS}'...")
            consumer = KafkaConsumer(
                KAFKA_TOPIC_ALERTS,
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='alert-sink-group'
            )
            logger.info("Alert Consumer connected successfully.")
            break
        except Exception as e:
            logger.warning(f"Consumer connection attempt failed: {e}. Retrying in 2s...")
            time.sleep(2)

    if not consumer:
        logger.error("Failed to connect Kafka consumer. Exiting.")
        sys.exit(1)

    try:
        for msg in consumer:
            alert = msg.value
            logger.info(f"Received alert from Kafka topic '{KAFKA_TOPIC_ALERTS}': {alert.get('alert_id')}")
            try:
                save_alert(db_conn, alert)
            except Exception as e:
                logger.error(f"Error persisting alert {alert.get('alert_id')}: {e}")
                # Reconnect DB if connection lost
                try:
                    db_conn = get_db_connection()
                except Exception:
                    pass
    except KeyboardInterrupt:
        logger.info("Shutting down Alert Sink.")
    finally:
        if consumer: consumer.close()
        if db_conn: db_conn.close()

if __name__ == "__main__":
    run_alert_sink()
