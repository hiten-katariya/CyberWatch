import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("ingest-producer")

# Environment configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_CONN = os.getenv("KAFKA_TOPIC_CONN", "events.conn")
KAFKA_TOPIC_DNS = os.getenv("KAFKA_TOPIC_DNS", "events.dns")
KAFKA_TOPIC_TLS = os.getenv("KAFKA_TOPIC_TLS", "events.tls")
SENSOR_ID = os.getenv("SENSOR_ID", "sensor-01")
ZEEK_LOG_DIR = os.getenv("ZEEK_LOG_DIR", "./sensor/logs")

def get_kafka_producer(broker_address, max_retries=10, retry_interval=3):
    """Attempt connection to Kafka broker with retry loop."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to Kafka broker at {broker_address} (Attempt {attempt}/{max_retries})...")
            producer = KafkaProducer(
                bootstrap_servers=broker_address,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3
            )
            logger.info("Successfully connected to Kafka broker.")
            return producer
        except Exception as e:
            logger.warning(f"Kafka connection failed: {e}. Retrying in {retry_interval}s...")
            time.sleep(retry_interval)
    logger.error("Failed to connect to Kafka after max retries.")
    return None

def safe_float(val, default=0.0):
    try:
        if val in ("-", "", None): return default
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        if val in ("-", "", None): return default
        return int(val)
    except (ValueError, TypeError):
        return default

def parse_zeek_ts(ts_val):
    """Convert Zeek epoch timestamp to ISO8601 string."""
    try:
        epoch = safe_float(ts_val, time.time())
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def parse_zeek_tsv_line(line, field_names):
    """Parse a single TSV line from Zeek log using header field names."""
    if not line or line.startswith("#"):
        return None
    parts = line.strip().split("\t")
    if len(parts) < len(field_names):
        logger.warning(f"Malformed TSV line (expected {len(field_names)} fields, got {len(parts)}): {line[:60]}")
        return None
    record = {}
    for idx, field in enumerate(field_names):
        if idx < len(parts):
            record[field] = parts[idx]
    return record

def normalize_conn_event(record):
    """Normalize raw Zeek conn.log record into canonical event schema."""
    ts = parse_zeek_ts(record.get("ts"))
    src_ip = record.get("id.orig_h", record.get("src_ip", "0.0.0.0"))
    dst_ip = record.get("id.resp_h", record.get("dst_ip", "0.0.0.0"))
    src_port = safe_int(record.get("id.orig_p", record.get("src_port")))
    dst_port = safe_int(record.get("id.resp_p", record.get("dst_port")))
    proto = str(record.get("proto", "tcp")).lower()
    duration = safe_float(record.get("duration"))
    orig_bytes = safe_int(record.get("orig_bytes"))
    resp_bytes = safe_int(record.get("resp_bytes"))

    return {
        "event_type": "conn",
        "timestamp": ts,
        "sensor_id": SENSOR_ID,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "proto": proto,
        "duration": duration,
        "orig_bytes": orig_bytes,
        "resp_bytes": resp_bytes
    }

def normalize_dns_event(record):
    """Normalize raw Zeek dns.log record."""
    return {
        "event_type": "dns",
        "timestamp": parse_zeek_ts(record.get("ts")),
        "sensor_id": SENSOR_ID,
        "src_ip": record.get("id.orig_h", "0.0.0.0"),
        "dst_ip": record.get("id.resp_h", "0.0.0.0"),
        "src_port": safe_int(record.get("id.orig_p")),
        "dst_port": safe_int(record.get("id.resp_p")),
        "proto": "udp",
        "query": record.get("query", ""),
        "qtype_name": record.get("qtype_name", ""),
        "rcode_name": record.get("rcode_name", "")
    }

def normalize_tls_event(record):
    """Normalize raw Zeek ssl/tls log record."""
    return {
        "event_type": "tls",
        "timestamp": parse_zeek_ts(record.get("ts")),
        "sensor_id": SENSOR_ID,
        "src_ip": record.get("id.orig_h", "0.0.0.0"),
        "dst_ip": record.get("id.resp_h", "0.0.0.0"),
        "src_port": safe_int(record.get("id.orig_p")),
        "dst_port": safe_int(record.get("id.resp_p")),
        "version": record.get("version", ""),
        "cipher": record.get("cipher", ""),
        "server_name": record.get("server_name", ""),
        "ja3": record.get("ja3", "")
    }

class ZeekLogTailer:
    """Tails Zeek log file (TSV or JSON) and yields parsed records."""
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.file_obj = None
        self.field_names = []
        self.last_pos = 0

    def read_new_lines(self):
        if not self.filepath.exists():
            return
        if self.file_obj is None:
            try:
                self.file_obj = open(self.filepath, "r", encoding="utf-8", errors="ignore")
                logger.info(f"Opened Zeek log for tailing: {self.filepath}")
            except Exception as e:
                logger.error(f"Failed to open log file {self.filepath}: {e}")
                return

        while True:
            line = self.file_obj.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            # Header parsing for Zeek TSV
            if line.startswith("#fields"):
                self.field_names = line.split("\t")[1:]
                logger.info(f"Parsed Zeek header fields for {self.filepath.name}: {self.field_names}")
                continue
            elif line.startswith("#"):
                continue

            # Try parsing as JSON first
            if line.startswith("{") and line.endswith("}"):
                try:
                    yield json.loads(line)
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON line: {line[:50]} error: {e}")

            # TSV parsing using header fields
            if self.field_names:
                rec = parse_zeek_tsv_line(line, self.field_names)
                if rec:
                    yield rec
            else:
                # Default fallback header if missing
                default_fields = ["ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto", "service", "duration", "orig_bytes", "resp_bytes"]
                rec = parse_zeek_tsv_line(line, default_fields)
                if rec:
                    yield rec

def main():
    logger.info("Starting Zeek -> Kafka Ingest Producer")
    producer = get_kafka_producer(KAFKA_BROKER)
    
    conn_log_path = Path(ZEEK_LOG_DIR) / "conn.log"
    dns_log_path = Path(ZEEK_LOG_DIR) / "dns.log"
    tls_log_path = Path(ZEEK_LOG_DIR) / "ssl.log"

    conn_tailer = ZeekLogTailer(conn_log_path)
    dns_tailer = ZeekLogTailer(dns_log_path)
    tls_tailer = ZeekLogTailer(tls_log_path)

    logger.info(f"Monitoring Zeek logs directory: {ZEEK_LOG_DIR}")

    try:
        while True:
            # Tail conn.log
            for raw_rec in conn_tailer.read_new_lines():
                event = normalize_conn_event(raw_rec)
                if producer:
                    producer.send(KAFKA_TOPIC_CONN, event)
                    logger.info(f"Published conn event: {event['src_ip']}:{event['src_port']} -> {event['dst_ip']}:{event['dst_port']} ({event['proto']})")

            # Tail dns.log
            for raw_rec in dns_tailer.read_new_lines():
                event = normalize_dns_event(raw_rec)
                if producer:
                    producer.send(KAFKA_TOPIC_DNS, event)
                    logger.info(f"Published dns event for query: {event.get('query')}")

            # Tail ssl/tls log
            for raw_rec in tls_tailer.read_new_lines():
                event = normalize_tls_event(raw_rec)
                if producer:
                    producer.send(KAFKA_TOPIC_TLS, event)
                    logger.info(f"Published tls event for server: {event.get('server_name')}")

            if producer:
                producer.flush()
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received for ingest producer.")
    finally:
        if producer:
            producer.close()
        logger.info("Ingest producer terminated cleanly.")

if __name__ == "__main__":
    main()
