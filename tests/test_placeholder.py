import pytest
import uuid

def process_event_sequence(events):
    alerts_fired = []
    alert_state = {"fired": False}

    for event in events:
        if not alert_state["fired"]:
            alert = {
                "schema_version": "1.0",
                "alert_id": str(uuid.uuid4()),
                "sensor_id": event.get("sensor_id", "sensor-01"),
                "threat_class": "test",
                "severity": "low",
                "confidence": 1.0,
                "flow_identifier": {
                    "src_ip": event.get("src_ip"),
                    "dst_ip": event.get("dst_ip"),
                    "src_port": event.get("src_port"),
                    "dst_port": event.get("dst_port"),
                    "proto": event.get("proto")
                },
                "evidence": {
                    "type": "phase1_placeholder",
                    "message": "Phase 1 pipeline verification alert"
                }
            }
            alerts_fired.append(alert)
            alert_state["fired"] = True
    return alerts_fired

def test_placeholder_detector_fires_exactly_once():
    events = [
        {"src_ip": "10.0.0.2", "dst_ip": "10.0.0.3", "src_port": 1234, "dst_port": 5201, "proto": "tcp"},
        {"src_ip": "10.0.0.2", "dst_ip": "10.0.0.3", "src_port": 1235, "dst_port": 5201, "proto": "tcp"},
        {"src_ip": "10.0.0.4", "dst_ip": "10.0.0.5", "src_port": 5678, "dst_port": 80, "proto": "tcp"},
    ]

    alerts = process_event_sequence(events)
    assert len(alerts) == 1
    first_alert = alerts[0]
    assert first_alert["threat_class"] == "test"
    assert first_alert["severity"] == "low"
    assert first_alert["confidence"] == 1.0
    assert first_alert["flow_identifier"]["src_ip"] == "10.0.0.2"
