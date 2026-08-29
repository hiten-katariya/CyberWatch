import pytest
from ingest.producer import parse_zeek_tsv_line, normalize_conn_event, normalize_dns_event

def test_parse_zeek_tsv_line():
    fields = ["ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto", "service", "duration", "orig_bytes", "resp_bytes"]
    line = "1735300000.123\tC12345\t10.0.0.2\t1234\t10.0.0.3\t5201\ttcp\t-\t1.25\t100\t200"
    rec = parse_zeek_tsv_line(line, fields)
    assert rec is not None
    assert rec["id.orig_h"] == "10.0.0.2"
    assert rec["id.resp_p"] == "5201"
    assert rec["proto"] == "tcp"

def test_normalize_conn_event():
    rec = {
        "ts": "1735300000.0",
        "id.orig_h": "10.0.0.2",
        "id.resp_h": "10.0.0.3",
        "id.orig_p": "1234",
        "id.resp_p": "5201",
        "proto": "tcp",
        "duration": "2.5",
        "orig_bytes": "500",
        "resp_bytes": "1000"
    }
    event = normalize_conn_event(rec)
    assert event["event_type"] == "conn"
    assert event["src_ip"] == "10.0.0.2"
    assert event["dst_ip"] == "10.0.0.3"
    assert event["src_port"] == 1234
    assert event["dst_port"] == 5201
    assert event["proto"] == "tcp"
    assert event["duration"] == 2.5
    assert event["orig_bytes"] == 500
    assert event["resp_bytes"] == 1000
