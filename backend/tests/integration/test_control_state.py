"""Tests for transactional control state, case versioning, and idempotency invariants."""

import pytest

from trade_operations_settlement.application.tools.records import (
    AuditEventRecord,
    CaseRecord,
    OutboxRecord,
)
from trade_operations_settlement.application.tools.state_store import (
    ConcurrencyError,
    ControlStateStore,
    DuplicateIdempotencyKeyError,
)


def test_intake_uniqueness_enforces_idempotency() -> None:
    store = ControlStateStore()
    case1 = CaseRecord(
        case_id="CAS-001",
        source_system="matching_engine",
        intake_idempotency_key="IDEMP-100",
        case_type="fee_break",
        state="received",
        case_version=1,
    )
    store.create_case(case1)

    case_duplicate = CaseRecord(
        case_id="CAS-002",
        source_system="matching_engine",
        intake_idempotency_key="IDEMP-100",
        case_type="fee_break",
        state="received",
        case_version=1,
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        store.create_case(case_duplicate)


def test_optimistic_concurrency_rejects_stale_case_version() -> None:
    store = ControlStateStore()
    case = CaseRecord(
        case_id="CAS-002",
        source_system="matching_engine",
        intake_idempotency_key="IDEMP-101",
        case_type="settlement_date_break",
        state="received",
        case_version=1,
    )
    store.create_case(case)

    # Valid update with matching version
    updated = store.update_case_state("CAS-002", expected_version=1, new_state="validated")
    assert updated.case_version == 2
    assert updated.state == "validated"

    # Stale update with old version 1 must raise ConcurrencyError
    with pytest.raises(ConcurrencyError):
        store.update_case_state("CAS-002", expected_version=1, new_state="screened")


def test_transactional_outbox_and_audit_creation() -> None:
    store = ControlStateStore()
    case = CaseRecord(
        case_id="CAS-003",
        source_system="swift",
        intake_idempotency_key="IDEMP-102",
        case_type="fee_break",
        state="received",
        case_version=1,
    )
    audit = AuditEventRecord(
        case_id="CAS-003",
        sequence_number=1,
        event_type="intake.accepted",
        actor="system",
        payload_hash="hash-123",
    )
    outbox = OutboxRecord(
        event_id="EVT-001",
        channel="trade-operations.case-events.v1",
        event_type="intake.accepted",
        payload={"case_id": "CAS-003"},
    )

    store.create_case_transactional(case, audit_event=audit, outbox_record=outbox)

    retrieved_case = store.get_case("CAS-003")
    assert retrieved_case is not None
    assert retrieved_case.case_id == "CAS-003"

    events = store.get_audit_events("CAS-003")
    assert len(events) == 1
    assert events[0].sequence_number == 1

    outbox_entries = store.get_pending_outbox()
    assert len(outbox_entries) >= 1
    assert any(entry.event_id == "EVT-001" for entry in outbox_entries)
