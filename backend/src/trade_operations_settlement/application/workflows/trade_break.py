"""Trade break resolution workflow orchestrating PortAgent 0.0.2 agents and deterministic controls.

Coordinates screening, evidence extraction, dispute detection, deterministic calculations,
and policy evaluation.
"""

from dataclasses import dataclass
from decimal import Decimal

from portagent.core.workflow import WorkflowDefinition, WorkflowEdge

from trade_operations_settlement.application.agents.trade_break import (
    BreakClassifierAgent,
    ChatConfirmReconciliationAgent,
    ConfirmationExtractorAgent,
    TradeEvidenceAgent,
    build_trade_break_agent_specs,
)
from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.policy_gate import (
    PolicyGate,
    PolicyGateInput,
    PolicyOutcomeEnum,
)
from trade_operations_settlement.application.tools.records import (
    CaseRecord,
    ProposalRecord,
)
from trade_operations_settlement.application.tools.state_store import ControlStateStore
from trade_operations_settlement.application.tools.trade_calculations import (
    aggregate_weakest_confidence,
    build_amendment_proposal,
    calculate_fee_difference,
)
from trade_operations_settlement.application.tools.trade_retrieval import (
    register_trade_retrieval_tools,
)
from trade_operations_settlement.application.workflows.runtime import PortAgentRuntime


@dataclass
class TradeBreakCaseInput:
    case_id: str
    chat_thread: list[dict[str, str]]
    confirm_text: str
    booked_fee: Decimal
    account_id: str
    currency: str = "USD"
    guardrail_triggered: bool = False
    exception_text: str = ""


class TradeBreakWorkflowService:
    def __init__(
        self,
        state_store: ControlStateStore,
        audit_writer: AuditWriter,
        policy_gate: PolicyGate,
        runtime: PortAgentRuntime | None = None,
    ) -> None:
        self.state_store = state_store
        self.audit_writer = audit_writer
        self.policy_gate = policy_gate
        self.runtime = runtime or PortAgentRuntime()
        self.runtime.initialize()

        # Register allowlisted read-only retrieval tools into PortAgent
        register_trade_retrieval_tools()

        # Build agent roster
        self.agent_specs = build_trade_break_agent_specs()

        # Define the PortAgent execution workflow graph
        self.workflow_definition = WorkflowDefinition(
            id="trade_break_resolution_v1",
            nodes=["break_classifier", "trade_evidence", "confirm_extractor", "reconciler"],
            edges=[
                WorkflowEdge(source="break_classifier", target="trade_evidence", type="sequential"),
                WorkflowEdge(source="trade_evidence", target="confirm_extractor", type="sequential"),
                WorkflowEdge(source="confirm_extractor", target="reconciler", type="sequential"),
            ],
        )

        # Interpreters for agent node processing
        self.break_classifier = BreakClassifierAgent()
        self.trade_agent = TradeEvidenceAgent()
        self.confirm_agent = ConfirmationExtractorAgent()
        self.reconciler = ChatConfirmReconciliationAgent()

    def execute(self, ctx: TradeBreakCaseInput) -> CaseRecord:
        case = self.state_store.get_case(ctx.case_id)
        if not case:
            raise KeyError(f"Case {ctx.case_id} not found")

        # 1. Untrusted content screening / Guardrails
        if ctx.guardrail_triggered:
            gate_input = PolicyGateInput(
                case_type=case.case_type,
                exposure_amount=case.exposure_amount,
                confidence=Decimal("0.99"),
                guardrail_triggered=True,
            )
            decision = self.policy_gate.evaluate(gate_input, case_id=case.case_id)
            case.failure_reason_codes = decision.reason_codes
            self.state_store.update_case_state(
                case.case_id,
                expected_version=case.case_version,
                new_state="rejected",
            )
            return case

        # 2. PortAgent-managed interpretation
        # Interpret chat thread
        chat_finding = self.trade_agent.interpret(ctx.chat_thread)
        agreed_val = chat_finding.field_value.get("fee", "0.00")

        # Interpret confirmation
        confirm_finding = self.confirm_agent.interpret(ctx.confirm_text)
        confirm_val = confirm_finding.field_value.get("fee", "0.00")

        # Reconcile semantic findings
        reconciliation_finding = self.reconciler.interpret(agreed_val, confirm_val)
        has_conflict = reconciliation_finding.is_conflict
        weakest_confidence = aggregate_weakest_confidence([chat_finding.confidence, confirm_finding.confidence])

        proposal: ProposalRecord | None = None

        if has_conflict:
            # Under evidence conflict: NO autonomous proposal survives
            case.failure_reason_codes.append("EVIDENCE_CONFLICT")
            gate_input = PolicyGateInput(
                case_type=case.case_type,
                exposure_amount=case.exposure_amount,
                confidence=weakest_confidence,
                has_evidence_conflict=True,
            )
            decision = self.policy_gate.evaluate(gate_input, case_id=case.case_id)
            new_state = "review_required"
        else:
            # 3. Deterministic calculation: agreed fee vs booked fee
            diff = calculate_fee_difference(booked=ctx.booked_fee, agreed=Decimal(agreed_val))
            proposal = build_amendment_proposal(
                case_id=case.case_id,
                account_id=ctx.account_id,
                difference_amount=diff,
                currency=ctx.currency,
                value_date="2026-09-24",
                reason_code="FEE_MISMATCH_RESOLVED",
            )
            case.current_proposal_id = proposal.proposal_id
            if not hasattr(self.state_store, "_proposals"):
                self.state_store._proposals = {}
            self.state_store._proposals[proposal.proposal_id] = proposal

            # 4. Deterministic policy evaluation outside all agents
            gate_input = PolicyGateInput(
                case_type=case.case_type,
                exposure_amount=abs(diff),
                confidence=weakest_confidence,
            )
            decision = self.policy_gate.evaluate(gate_input, case_id=case.case_id)
            new_state = (
                "ready_to_post"
                if decision.outcome == PolicyOutcomeEnum.AUTONOMOUS_AUTHORIZED.value
                else "review_required"
            )

        case.current_policy_decision_id = decision.decision_id
        if not hasattr(self.state_store, "_policy_decisions"):
            self.state_store._policy_decisions = {}
        self.state_store._policy_decisions[decision.decision_id] = decision

        self.state_store.update_case_state(
            case.case_id,
            expected_version=case.case_version,
            new_state=new_state,
        )

        # 5. Audit trail
        self.audit_writer.record_event(
            case_id=case.case_id,
            event_type="workflow.trade_break.completed",
            actor="trade_break_workflow",
            details={
                "workflow_id": self.workflow_definition.id,
                "has_conflict": has_conflict,
                "confidence": str(weakest_confidence),
                "policy_outcome": decision.outcome,
                "proposal_id": proposal.proposal_id if proposal else None,
            },
        )
        return case
