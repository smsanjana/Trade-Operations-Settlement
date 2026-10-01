"""Deterministic policy gate: outside all agents and model reasoning.

Evaluates type eligibility, confidence, exposure amounts, dual-control thresholds,
and hard blocks (conflicts, missing evidence, guardrails) with stable reason codes.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from trade_operations_settlement.application.tools.records import (
    PolicyConfigurationRecord,
    PolicyDecisionRecord,
    utc_now,
)


class PolicyOutcomeEnum(str, Enum):
    REJECTED = "rejected"
    APPROVAL_REQUIRED = "approval_required"
    DUAL_CONTROL_REQUIRED = "dual_control_required"
    AUTONOMOUS_AUTHORIZED = "autonomous_authorized"


@dataclass
class PolicyGateInput:
    case_type: str
    exposure_amount: Decimal
    confidence: Decimal
    has_evidence_conflict: bool = False
    has_missing_evidence: bool = False
    guardrail_triggered: bool = False
    agent_requested_escalation: bool = False


class PolicyGate:
    def __init__(self, policy: PolicyConfigurationRecord) -> None:
        self.policy = policy

    def evaluate(self, inp: PolicyGateInput, case_id: str) -> PolicyDecisionRecord:
        decision_id = f"POL-{uuid.uuid4().hex[:8].upper()}"
        reasons: list[str] = []
        outcome: str

        # 1. Hard block precedence: Guardrails triggered forces rejection
        if inp.guardrail_triggered:
            outcome = PolicyOutcomeEnum.REJECTED.value
            reasons.append("GUARDRAIL_BLOCKED")
        elif inp.has_evidence_conflict:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("EVIDENCE_CONFLICT")
        elif inp.has_missing_evidence:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("MISSING_EVIDENCE")
        elif inp.agent_requested_escalation:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("AGENT_ESCALATION_REQUESTED")
        elif inp.case_type not in self.policy.eligible_case_types:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("CASE_TYPE_INELIGIBLE")
        elif inp.confidence < self.policy.confidence_threshold:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("CONFIDENCE_BELOW_THRESHOLD")
        elif inp.exposure_amount > self.policy.dual_control_threshold:
            outcome = PolicyOutcomeEnum.DUAL_CONTROL_REQUIRED.value
            reasons.append("DUAL_CONTROL_REQUIRED")
        elif inp.exposure_amount > self.policy.auto_post_limit:
            outcome = PolicyOutcomeEnum.APPROVAL_REQUIRED.value
            reasons.append("EXPOSURE_EXCEEDS_AUTONOMOUS_LIMIT")
        else:
            outcome = PolicyOutcomeEnum.AUTONOMOUS_AUTHORIZED.value
            reasons.append("AUTONOMOUS_AUTHORIZED")

        inputs_snapshot: dict[str, Any] = {
            "case_type": inp.case_type,
            "exposure_amount": str(inp.exposure_amount),
            "confidence": str(inp.confidence),
            "has_evidence_conflict": inp.has_evidence_conflict,
            "has_missing_evidence": inp.has_missing_evidence,
            "guardrail_triggered": inp.guardrail_triggered,
            "agent_requested_escalation": inp.agent_requested_escalation,
        }

        return PolicyDecisionRecord(
            decision_id=decision_id,
            case_id=case_id,
            policy_version=self.policy.policy_version,
            outcome=outcome,
            reason_codes=reasons,
            evaluated_at=utc_now(),
            inputs_snapshot=inputs_snapshot,
        )
