"""End-to-end tests for PortAgent-orchestrated trade break resolution workflow."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.policy_gate import PolicyGate
from trade_operations_settlement.application.tools.records import (
    CaseRecord,
    PolicyConfigurationRecord,
)
from trade_operations_settlement.application.tools.state_store import ControlStateStore
from trade_operations_settlement.application.workflows.runtime import PortAgentRuntime
from trade_operations_settlement.application.workflows.trade_break import (
    TradeBreakCaseInput,
    TradeBreakWorkflowService,
)


@pytest.fixture
def store():
    return ControlStateStore()


@pytest.fixture
def audit(store):
    return AuditWriter(store)


@pytest.fixture
def runtime():
    r = PortAgentRuntime()
    r.initialize()
    return r


@pytest.fixture
def policy():
    return PolicyConfigurationRecord(
        policy_version="2026.1",
        desk_id="EQ_LON",
        confidence_threshold=Decimal("0.90"),
        auto_post_limit=Decimal("500.00"),
        dual_control_threshold=Decimal("10000.00"),
        eligible_case_types=["fee_break"],
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_agreeing_fee_break_within_threshold_auto_posts(store, audit, runtime, policy):
    case = CaseRecord(
        case_id="CAS-TB-001",
        case_version=1,
        case_type="fee_break",
        state="received",
        priority="normal",
        counterparty_or_custodian="CITI_LON",
        exposure_amount=Decimal("250.00"),
        source_system="DTCC",
        intake_idempotency_key="DTCC-TB-1",
        desk_id="EQ_LON",
    )
    store.create_case(case)

    service = TradeBreakWorkflowService(
        state_store=store,
        audit_writer=audit,
        policy_gate=PolicyGate(policy),
        runtime=runtime,
    )

    case_input = TradeBreakCaseInput(
        case_id="CAS-TB-001",
        chat_thread=[{"msg_id": "1", "sender": "Trader", "text": "Agreed fee is 250.00 USD"}],
        confirm_text="Electronic Trade Confirmation: Fee 250.00 USD",
        booked_fee=Decimal("0.00"),
        account_id="ACC-FEE-01",
        currency="USD",
    )

    result_case = service.execute(case_input)
    assert result_case.state == "ready_to_post"
    assert result_case.case_version == 2
    assert result_case.current_proposal_id is not None


def test_disputed_fee_break_escalates_to_review(store, audit, runtime, policy):
    case = CaseRecord(
        case_id="CAS-TB-002",
        case_version=1,
        case_type="fee_break",
        state="received",
        priority="high",
        counterparty_or_custodian="CITI_LON",
        exposure_amount=Decimal("300.00"),
        source_system="DTCC",
        intake_idempotency_key="DTCC-TB-2",
        desk_id="EQ_LON",
    )
    store.create_case(case)

    service = TradeBreakWorkflowService(
        state_store=store,
        audit_writer=audit,
        policy_gate=PolicyGate(policy),
        runtime=runtime,
    )

    case_input = TradeBreakCaseInput(
        case_id="CAS-TB-002",
        chat_thread=[{"msg_id": "1", "sender": "Trader", "text": "Agreed fee is 250.00 USD"}],
        confirm_text="Electronic Trade Confirmation: Fee 350.00 USD",  # Mismatch!
        booked_fee=Decimal("0.00"),
        account_id="ACC-FEE-02",
        currency="USD",
    )

    result_case = service.execute(case_input)
    assert result_case.state == "review_required"
    assert "EVIDENCE_CONFLICT" in result_case.failure_reason_codes
