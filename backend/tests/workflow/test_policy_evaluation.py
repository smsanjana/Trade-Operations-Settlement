"""Workflow tests for deterministic policy evaluation and fail-closed behavior."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.policy_gate import (
    PolicyGate,
    PolicyGateInput,
)
from trade_operations_settlement.application.tools.records import (
    CaseRecord,
    PolicyConfigurationRecord,
)
from trade_operations_settlement.application.tools.state_store import ControlStateStore
from trade_operations_settlement.application.workflows.policy_evaluation import (
    PolicyEvaluationService,
)


@pytest.fixture
def store():
    return ControlStateStore()


@pytest.fixture
def audit(store):
    return AuditWriter(store)


@pytest.fixture
def active_policy():
    return PolicyConfigurationRecord(
        policy_version="2026.1",
        desk_id="EQ_LON",
        confidence_threshold=Decimal("0.95"),
        auto_post_limit=Decimal("500.00"),
        dual_control_threshold=Decimal("10000.00"),
        eligible_case_types=["fee_break"],
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_policy_evaluation_updates_case_state_and_audits(store, audit, active_policy):
    case = CaseRecord(
        case_id="CAS-POL-001",
        case_version=1,
        case_type="fee_break",
        state="received",
        priority="normal",
        counterparty_or_custodian="BARCLAYS",
        exposure_amount=Decimal("120.00"),
        source_system="DTCC",
        intake_idempotency_key="KEY-POL-1",
        desk_id="EQ_LON",
    )
    store.create_case(case)

    gate = PolicyGate(active_policy)
    service = PolicyEvaluationService(gate, store, audit)

    gate_input = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("120.00"),
        confidence=Decimal("0.97"),
    )
    decision = service.evaluate_case("CAS-POL-001", gate_input)
    assert decision.outcome == "autonomous_authorized"

    updated_case = store.get_case("CAS-POL-001")
    assert updated_case.state == "ready_to_post"
    assert updated_case.case_version == 2

    # Audit recorded
    events = store.get_audit_events("CAS-POL-001")
    assert len(events) == 1
    assert events[0].event_type == "policy.evaluated"


def test_missing_case_raises_key_error(store, audit, active_policy):
    gate = PolicyGate(active_policy)
    service = PolicyEvaluationService(gate, store, audit)
    gate_input = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("10.00"),
        confidence=Decimal("0.99"),
    )
    with pytest.raises(KeyError):
        service.evaluate_case("NON-EXISTENT", gate_input)
