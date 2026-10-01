"""Contract tests for settlement exception intake events and validation."""

from decimal import Decimal

from trade_operations_settlement.api.intake import IntakeEventEnvelope, IntakeService
from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.state_store import (
    ControlStateStore,
)


def test_valid_settlement_intake_creates_case():
    store = ControlStateStore()
    audit = AuditWriter(store)
    intake = IntakeService(store, audit)

    envelope = IntakeEventEnvelope(
        event_id="EVT-INTAKE-1",
        source_system="DTCC",
        idempotency_key="DTCC-TX-9988",
        event_type="settlement.exception.received",
        payload={
            "break_type": "fee_break",
            "counterparty": "CITI_LON",
            "instrument": "GB0002634946",
            "expected_amount": "12450.00",
            "booked_amount": "12000.00",
            "currency": "GBP",
            "desk_id": "EQ_LON",
        },
    )

    case = intake.process_intake(envelope)
    assert case.case_id.startswith("CAS-")
    assert case.state == "received"
    assert case.case_type == "fee_break"
    assert case.exposure_amount == Decimal("450.00")


def test_duplicate_intake_is_deduplicated():
    store = ControlStateStore()
    audit = AuditWriter(store)
    intake = IntakeService(store, audit)

    envelope = IntakeEventEnvelope(
        event_id="EVT-INTAKE-2",
        source_system="DTCC",
        idempotency_key="DTCC-TX-DUP",
        event_type="settlement.exception.received",
        payload={
            "break_type": "settlement_date_break",
            "counterparty": "BARCLAYS",
            "instrument": "US0378331005",
            "currency": "USD",
            "desk_id": "EQ_NY",
        },
    )

    case1 = intake.process_intake(envelope)
    # Second delivery with same source and idempotency_key is deduplicated
    case2 = intake.process_intake(envelope)
    assert case1.case_id == case2.case_id
    assert case2.case_version == case1.case_version
