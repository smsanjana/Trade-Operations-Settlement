"""Integration tests for Starlette ASGI API endpoints matching OpenAPI 3.1 contracts."""

import pytest
from starlette.testclient import TestClient

from trade_operations_settlement.api.main import app, seed_synthetic_fixtures, state_store


@pytest.fixture(autouse=True)
def reset_fixtures():
    state_store._cases.clear()
    state_store._inbox.clear()
    state_store._audit_events.clear()
    state_store._outbox.clear()
    seed_synthetic_fixtures()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["portagent_runtime"] == "operational"


def test_list_cases_with_filtering_and_sorting(client: TestClient) -> None:
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 4

    # Test filtering by priority
    resp_filtered = client.get("/api/v1/cases?priority=Critical")
    assert resp_filtered.status_code == 200
    items = resp_filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["case_id"] == "CA-77104"

    # Test filtering by state
    resp_state = client.get("/api/v1/cases?state=posted")
    assert resp_state.status_code == 200
    items = resp_state.json()["items"]
    assert len(items) == 1
    assert items[0]["case_id"] == "CA-77098"


def test_get_case_snapshot_and_etag(client: TestClient) -> None:
    response = client.get("/api/v1/cases/TRD-28419")
    assert response.status_code == 200
    assert response.headers.get("etag") == '"TRD-28419-v1"'
    snapshot = response.json()
    assert snapshot["case_id"] == "TRD-28419"
    assert snapshot["proposal"]["amount"] == "450.00"
    assert snapshot["policy_decision"]["outcome"] == "approval_required"
    assert len(snapshot["evidence_citations"]) == 2


def test_get_nonexistent_case_returns_rfc9457_404(client: TestClient) -> None:
    response = client.get("/api/v1/cases/DOES_NOT_EXIST")
    assert response.status_code == 404
    assert response.headers.get("content-type") == "application/problem+json"
    problem = response.json()
    assert problem["status"] == 404
    assert problem["title"] == "Not Found"


def test_list_and_get_case_evidence(client: TestClient) -> None:
    resp = client.get("/api/v1/cases/TRD-28419/evidence")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["evidence_id"] == "EV-CHAT-001"

    rendition = client.get("/api/v1/cases/TRD-28419/evidence/EV-CHAT-001")
    assert rendition.status_code == 200
    r_data = rendition.json()
    assert r_data["evidence_id"] == "EV-CHAT-001"
    assert "Agreed final commission" in r_data["excerpt"]


def test_list_case_audit_events(client: TestClient) -> None:
    resp = client.get("/api/v1/cases/TRD-28419/audit-events")
    assert resp.status_code == 200
    events = resp.json()["items"]
    assert len(events) >= 1
    assert events[0]["event_type"] == "intake.received"


def test_decision_requires_if_match_header(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        json={"action": "approve", "note": "LGTM"},
    )
    assert resp.status_code == 412
    assert resp.json()["title"] == "Precondition Failed"


def test_decision_stale_etag_returns_rfc9457_409_conflict(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        headers={"if-match": '"TRD-28419-v999"'},
        json={"action": "approve", "note": "LGTM"},
    )
    assert resp.status_code == 409
    assert resp.json()["title"] == "Conflict"


def test_decision_rejects_client_authored_approver_identity(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        headers={"if-match": '"TRD-28419-v1"'},
        json={"action": "approve", "approver_id": "malicious_actor", "note": "LGTM"},
    )
    assert resp.status_code == 422
    assert resp.json()["title"] == "Unprocessable Content"


def test_decision_rejects_agent_role_attempting_approval(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        headers={
            "if-match": '"TRD-28419-v1"',
            "x-user-id": "autonomous_agent",
            "x-user-role": "agent",
        },
        json={"action": "approve", "note": "Agent approval"},
    )
    assert resp.status_code == 403
    assert resp.json()["title"] == "Forbidden"


def test_decision_amend_requires_note_and_recalculates(client: TestClient) -> None:
    # Missing note on amend
    resp_no_note = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        headers={"if-match": '"TRD-28419-v1"'},
        json={"action": "amend", "note": "", "amended_amount": "400.00"},
    )
    assert resp_no_note.status_code == 422

    # Valid amend
    resp = client.post(
        "/api/v1/cases/TRD-28419/decisions",
        headers={"if-match": '"TRD-28419-v1"'},
        json={"action": "amend", "note": "Adjust to net amount", "amended_amount": "400.00"},
    )
    assert resp.status_code == 201
    assert resp.headers.get("etag") == '"TRD-28419-v2"'
    data = resp.json()
    assert data["case_version"] == 2
    assert data["proposal"]["amount"] == "400.00"


def test_decision_dual_control_identity_reuse_prevented(client: TestClient) -> None:
    # CA-77104 was already approved by supervisor.a
    resp_reuse = client.post(
        "/api/v1/cases/CA-77104/decisions",
        headers={
            "if-match": '"CA-77104-v1"',
            "x-user-id": "supervisor.a",
            "x-user-role": "supervisor",
        },
        json={"action": "approve", "note": "Second approval by same supervisor"},
    )
    assert resp_reuse.status_code == 409
    assert "Dual-control identity reuse prohibited" in resp_reuse.json()["detail"]

    # Distinct second approver succeeds and moves to posted
    resp_second = client.post(
        "/api/v1/cases/CA-77104/decisions",
        headers={
            "if-match": '"CA-77104-v1"',
            "x-user-id": "supervisor.b",
            "x-user-role": "supervisor",
        },
        json={"action": "approve", "note": "Second control verified."},
    )
    assert resp_second.status_code == 201
    assert resp_second.json()["status"] == "posted"
    assert resp_second.headers.get("etag") == '"CA-77104-v2"'


def test_voluntary_desk_instruction_rejects_agent(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cases/TRD-28419/desk-instructions",
        headers={
            "x-user-id": "portagent-worker",
            "x-user-role": "agent",
        },
        json={"election": "TAKE_CASH"},
    )
    assert resp.status_code == 403
    assert resp.json()["title"] == "Forbidden"
