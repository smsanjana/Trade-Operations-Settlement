"""Unit tests for deterministic policy decision-table and threshold boundaries."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trade_operations_settlement.application.tools.policy_gate import (
    PolicyGate,
    PolicyGateInput,
    PolicyOutcomeEnum,
)
from trade_operations_settlement.application.tools.records import PolicyConfigurationRecord


@pytest.fixture
def sample_policy():
    return PolicyConfigurationRecord(
        policy_version="2026.1",
        desk_id="EQ_LON",
        confidence_threshold=Decimal("0.95"),
        auto_post_limit=Decimal("500.00"),
        dual_control_threshold=Decimal("10000.00"),
        eligible_case_types=["fee_break", "commission_break"],
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_autonomous_authorized_when_all_criteria_satisfied(sample_policy):
    gate = PolicyGate(sample_policy)
    inp = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("250.00"),
        confidence=Decimal("0.98"),
    )
    decision = gate.evaluate(inp, case_id="CAS-001")
    assert decision.outcome == PolicyOutcomeEnum.AUTONOMOUS_AUTHORIZED.value
    assert "AUTONOMOUS_AUTHORIZED" in decision.reason_codes


def test_guardrail_block_forces_rejection(sample_policy):
    gate = PolicyGate(sample_policy)
    inp = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("100.00"),
        confidence=Decimal("0.99"),
        guardrail_triggered=True,
    )
    decision = gate.evaluate(inp, case_id="CAS-002")
    assert decision.outcome == PolicyOutcomeEnum.REJECTED.value
    assert "GUARDRAIL_BLOCKED" in decision.reason_codes


def test_evidence_conflict_requires_human_approval(sample_policy):
    gate = PolicyGate(sample_policy)
    inp = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("100.00"),
        confidence=Decimal("0.99"),
        has_evidence_conflict=True,
    )
    decision = gate.evaluate(inp, case_id="CAS-003")
    assert decision.outcome == PolicyOutcomeEnum.APPROVAL_REQUIRED.value
    assert "EVIDENCE_CONFLICT" in decision.reason_codes


def test_exposure_above_dual_control_threshold(sample_policy):
    gate = PolicyGate(sample_policy)
    inp = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("15000.00"),
        confidence=Decimal("0.99"),
    )
    decision = gate.evaluate(inp, case_id="CAS-004")
    assert decision.outcome == PolicyOutcomeEnum.DUAL_CONTROL_REQUIRED.value
    assert "DUAL_CONTROL_REQUIRED" in decision.reason_codes


def test_ineligible_case_type_requires_approval(sample_policy):
    gate = PolicyGate(sample_policy)
    inp = PolicyGateInput(
        case_type="unsupported_exotic",
        exposure_amount=Decimal("50.00"),
        confidence=Decimal("0.99"),
    )
    decision = gate.evaluate(inp, case_id="CAS-005")
    assert decision.outcome == PolicyOutcomeEnum.APPROVAL_REQUIRED.value
    assert "CASE_TYPE_INELIGIBLE" in decision.reason_codes
