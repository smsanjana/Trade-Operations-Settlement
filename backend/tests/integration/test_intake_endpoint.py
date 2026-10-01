"""Integration tests for the HTTP intake event adapter endpoint (POST /api/v1/intake/events).

Validates schema validation, idempotency deduplication, audit logging,
and review queue availability without direct database or CRUD bypass.
"""

from decimal import Decimal
from starlette.testclient import TestClient

from trade_operations_settlement.api.main import app, state_store


def test_settlement_exception_intake_creates_case():
    client = TestClient(app)
    payload = {
        "event_id": "EVT-TEST-SETTL-1",
        "source_system": "MUREX",
        "idempotency_key": "IDEMP-SETTL-TEST-001",
        "event_type": "settlement.exception.received",
        "payload": {
            "break_type": "Fee mismatch",
            "counterparty": "Goldman Sachs Intl",
            "instrument": "US0378331005",
            "expected_amount": "15400.00",
            "booked_amount": "15000.00",
            "currency": "USD",
            "desk_id": "EQ_NY",
            "evidence_snippets": [
                {
                    "source_name": "Trader-broker chat",
                    "media_type": "text/plain",
                    "excerpt": "Confirmed fee should be USD 15,400.",
                }
            ],
        },
    }

    response = client.post("/api/v1/intake/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"].startswith("CAS-")
    assert data["case_type"] == "Fee mismatch"
    assert data["state"] == "received"
    assert data["exposure_amount"] == "400.00"
    assert data["deduplicated"] is False
    assert "successfully created" in data["message"]

    # Verify case exists in state store
    case = state_store.get_case(data["case_id"])
    assert case is not None
    assert case.source_system == "MUREX"
    assert case.exposure_amount == Decimal("400.00")

    # Verify audit event recorded
    audit_events = state_store.get_audit_events(data["case_id"])
    assert len(audit_events) >= 1
    assert audit_events[0].event_type == "intake.received"

    # Verify case is visible in GET /api/v1/cases
    list_resp = client.get("/api/v1/cases")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    matching = [i for i in items if i["case_id"] == data["case_id"]]
    assert len(matching) == 1

    # Verify snapshot can be retrieved
    snap_resp = client.get(f"/api/v1/cases/{data['case_id']}")
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    assert snap_data["case_id"] == data["case_id"]
    assert len(snap_data["evidence_citations"]) >= 1


def test_corporate_action_intake_creates_case():
    client = TestClient(app)
    payload = {
        "event_id": "EVT-TEST-CA-1",
        "source_system": "SWIFT",
        "idempotency_key": "IDEMP-CA-TEST-002",
        "event_type": "corporate_action.received",
        "payload": {
            "event_type": "Cash dividend",
            "mandatory_or_voluntary": "mandatory",
            "counterparty_or_custodian": "BNY Mellon",
            "instrument_id": "GB0002634946",
            "currency": "GBP",
            "amount": "8500.00",
            "desk_id": "CA_LON",
        },
    }

    response = client.post("/api/v1/intake/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"].startswith("CAS-")
    assert data["case_type"] == "Cash dividend"
    assert data["state"] == "received"
    assert data["exposure_amount"] == "8500.00"
    assert data["priority"] == "high"


def test_voluntary_corporate_action_with_deadline():
    client = TestClient(app)
    payload = {
        "event_id": "EVT-TEST-VOL-1",
        "source_system": "EUROCLEAR",
        "idempotency_key": "IDEMP-VOL-TEST-003",
        "event_type": "corporate_action.received",
        "payload": {
            "event_type": "Rights issue",
            "mandatory_or_voluntary": "voluntary",
            "counterparty_or_custodian": "Euroclear Bank",
            "instrument_id": "FR0000120271",
            "currency": "EUR",
            "amount": "25000.00",
            "deadline_at": "2026-10-15T16:00:00Z",
            "desk_id": "CA_PARIS",
        },
    }

    response = client.post("/api/v1/intake/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "high"

    # Verify deadline recorded on case
    case = state_store.get_case(data["case_id"])
    assert case is not None
    assert case.deadline_at is not None


def test_intake_idempotency_deduplication():
    client = TestClient(app)
    payload = {
        "event_id": "EVT-DUP-1",
        "source_system": "DTCC",
        "idempotency_key": "IDEMP-DUP-TEST-004",
        "event_type": "settlement.exception.received",
        "payload": {
            "break_type": "Commission break",
            "counterparty": "Morgan Stanley",
            "instrument": "US1104193065",
            "expected_amount": "500.00",
            "booked_amount": "400.00",
            "currency": "USD",
        },
    }

    # Initial submission -> 201 Created
    resp1 = client.post("/api/v1/intake/events", json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["deduplicated"] is False

    # Second submission with same (source_system, idempotency_key) -> 200 OK
    resp2 = client.post("/api/v1/intake/events", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["deduplicated"] is True
    assert data2["case_id"] == data1["case_id"]
    assert "Existing case" in data2["message"]

    # Verify deduplication audit event appended
    audit_events = state_store.get_audit_events(data1["case_id"])
    event_types = [e.event_type for e in audit_events]
    assert "intake.received" in event_types
    assert "intake.deduplicated" in event_types


def test_intake_validation_rejects_missing_fields():
    client = TestClient(app)

    # Missing source_system
    resp = client.post(
        "/api/v1/intake/events",
        json={"idempotency_key": "K1", "event_type": "settlement.exception.received", "payload": {}},
    )
    assert resp.status_code == 422

    # Missing idempotency_key
    resp = client.post(
        "/api/v1/intake/events",
        json={"source_system": "MUREX", "event_type": "settlement.exception.received", "payload": {}},
    )
    assert resp.status_code == 422

    # Invalid event_type
    resp = client.post(
        "/api/v1/intake/events",
        json={
            "source_system": "MUREX",
            "idempotency_key": "K2",
            "event_type": "unknown.event.type",
            "payload": {},
        },
    )
    assert resp.status_code == 422

    # Voluntary corporate action without deadline
    resp = client.post(
        "/api/v1/intake/events",
        json={
            "source_system": "SWIFT",
            "idempotency_key": "K3",
            "event_type": "corporate_action.received",
            "payload": {
                "event_type": "Tender offer",
                "mandatory_or_voluntary": "voluntary",
            },
        },
    )
    assert resp.status_code == 422
