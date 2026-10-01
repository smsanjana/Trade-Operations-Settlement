"""Deterministic policy evaluation workflow service: evaluates policy gate,

updates durable case state, and appends audit event within the transaction.
"""

from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.policy_gate import (
    PolicyGate,
    PolicyGateInput,
    PolicyOutcomeEnum,
)
from trade_operations_settlement.application.tools.records import PolicyDecisionRecord
from trade_operations_settlement.application.tools.state_store import ControlStateStore


class PolicyEvaluationService:
    def __init__(
        self,
        gate: PolicyGate,
        state_store: ControlStateStore,
        audit_writer: AuditWriter,
    ) -> None:
        self.gate = gate
        self.state_store = state_store
        self.audit_writer = audit_writer

    def evaluate_case(self, case_id: str, gate_input: PolicyGateInput) -> PolicyDecisionRecord:
        case = self.state_store.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        decision = self.gate.evaluate(gate_input, case_id=case_id)

        # Map policy outcome to authoritative case state
        if decision.outcome == PolicyOutcomeEnum.REJECTED.value:
            new_state = "rejected"
        elif decision.outcome == PolicyOutcomeEnum.DUAL_CONTROL_REQUIRED.value:
            new_state = "dual_control_required"
        elif decision.outcome == PolicyOutcomeEnum.APPROVAL_REQUIRED.value:
            new_state = "review_required"
        elif decision.outcome == PolicyOutcomeEnum.AUTONOMOUS_AUTHORIZED.value:
            new_state = "ready_to_post"
        else:
            new_state = "blocked"

        case.current_policy_decision_id = decision.decision_id
        self.state_store.update_case_state(
            case_id,
            expected_version=case.case_version,
            new_state=new_state,
        )

        self.audit_writer.record_event(
            case_id=case_id,
            event_type="policy.evaluated",
            actor="policy_gate",
            details={
                "policy_version": decision.policy_version,
                "outcome": decision.outcome,
                "reason_codes": decision.reason_codes,
                "inputs_snapshot": decision.inputs_snapshot,
            },
        )

        return decision
