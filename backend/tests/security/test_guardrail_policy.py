"""Security tests proving guardrail blocks deny all autonomous outcomes."""

from datetime import UTC, datetime
from decimal import Decimal

from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.policy_gate import (
    PolicyGate,
    PolicyGateInput,
    PolicyOutcomeEnum,
)
from trade_operations_settlement.application.tools.records import (
    CaseRecord,
    PolicyConfigurationRecord,
)
from trade_operations_settlement.application.tools.state_store import ControlStateStore
from trade_operations_settlement.application.workflows.policy_evaluation import (
    PolicyEvaluationService,
)


def test_guardrail_block_invalidates_proposal_and_denies_autonomy():
    store = ControlStateStore()
    audit = AuditWriter(store)

    case = CaseRecord(
        case_id="CAS-SEC-001",
        case_version=1,
        case_type="fee_break",
        state="received",
        priority="high",
        counterparty_or_custodian="CITI",
        exposure_amount=Decimal("50.00"),
        source_system="DTCC",
        intake_idempotency_key="SEC-1",
        desk_id="EQ_LON",
    )
    store.create_case(case)

    policy = PolicyConfigurationRecord(
        policy_version="2026.1",
        desk_id="EQ_LON",
        confidence_threshold=Decimal("0.90"),
        auto_post_limit=Decimal("5000.00"),
        dual_control_threshold=Decimal("100000.00"),
        eligible_case_types=["fee_break"],
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )

    gate = PolicyGate(policy)
    service = PolicyEvaluationService(gate, store, audit)

    # Even though amount is 50.00 (within limit) and confidence is 0.99,
    # guardrail_triggered MUST reject and deny autonomous execution
    gate_input = PolicyGateInput(
        case_type="fee_break",
        exposure_amount=Decimal("50.00"),
        confidence=Decimal("0.99"),
        guardrail_triggered=True,
    )

    decision = service.evaluate_case("CAS-SEC-001", gate_input)
    assert decision.outcome == PolicyOutcomeEnum.REJECTED.value
    assert "GUARDRAIL_BLOCKED" in decision.reason_codes

    updated_case = store.get_case("CAS-SEC-001")
    assert updated_case.state == "rejected"
