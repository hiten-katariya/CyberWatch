import os
import sys
import json
import asyncio
import logging
from typing import List, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from kafka import KafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("api-backend")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")

DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DB_NAME = os.getenv("DATABASE_NAME", "threatpipe")
DB_USER = os.getenv("DATABASE_USER", "postgres")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "threatpipe")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                dead_connections.add(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Database: {e}")
        return None

async def kafka_alert_listener():
    logger.info(f"Starting Kafka alert listener for WebSocket broadcast on topic '{KAFKA_TOPIC_ALERTS}'")
    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC_ALERTS,
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id=f'api-ws-broadcast-group-{os.getpid()}'
            )
            logger.info("Kafka consumer connected for WebSocket streaming.")
            loop = asyncio.get_event_loop()
            
            while True:
                records = await loop.run_in_executor(None, consumer.poll, 500)
                for topic_partition, messages in records.items():
                    for msg in messages:
                        alert = msg.value
                        logger.info(f"API broadcasting live alert over WS: {alert.get('alert_id')}")
                        await manager.broadcast(alert)
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Kafka consumer issue in API: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Backend starting up...")
    listener_task = asyncio.create_task(kafka_alert_listener())
    yield
    listener_task.cancel()
    logger.info("FastAPI Backend shutting down...")

app = FastAPI(
    title="Passive Threat Detection Platform API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    db_status = "ok"
    db_conn = get_db_connection()
    if not db_conn:
        db_status = "error"
    else:
        db_conn.close()

    kafka_status = "ok"
    try:
        c = KafkaConsumer(bootstrap_servers=KAFKA_BROKER, request_timeout_ms=1000)
        c.close()
    except Exception:
        kafka_status = "error"

    status_code = 200 if (db_status == "ok" and kafka_status == "ok") else 503
    return {
        "status": "degraded" if status_code == 503 else "healthy",
        "database": db_status,
        "kafka": kafka_status,
        "service": "api-backend"
    }

@app.get("/alerts")
def get_alerts(limit: int = 100):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT %s;", (limit,))
            rows = cur.fetchall()
            alerts = []
            for row in rows:
                row["alert_id"] = str(row["alert_id"])
                row["timestamp"] = row["timestamp"].isoformat()
                if "created_at" in row and row["created_at"]:
                    row["created_at"] = row["created_at"].isoformat()
                alerts.append(row)
            return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/alerts/stats")
def get_alert_stats():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT count(*) as total FROM alerts;")
            total = cur.fetchone()["total"]

            cur.execute("SELECT severity, count(*) as count FROM alerts GROUP BY severity;")
            sev_rows = cur.fetchall()
            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for r in sev_rows:
                s = str(r["severity"]).lower()
                if s in sev_counts:
                    sev_counts[s] = r["count"]

            cur.execute("SELECT threat_class, count(*) as count FROM alerts GROUP BY threat_class;")
            threat_rows = cur.fetchall()
            by_threat = {r["threat_class"]: r["count"] for r in threat_rows}

            return {
                "total": total,
                "critical": sev_counts["critical"],
                "high": sev_counts["high"],
                "medium": sev_counts["medium"],
                "low": sev_counts["low"],
                "by_threat": by_threat
            }
    except Exception as e:
        logger.error(f"Error fetching alert stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/alerts/{alert_id}")
def get_alert_by_id(alert_id: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM alerts WHERE alert_id = %s;", (alert_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Alert not found")
            row["alert_id"] = str(row["alert_id"])
            row["timestamp"] = row["timestamp"].isoformat()
            if "created_at" in row and row["created_at"]:
                row["created_at"] = row["created_at"].isoformat()
            return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("API_HOST", "0.0.0.0"), port=int(os.getenv("API_PORT", 8000)))
