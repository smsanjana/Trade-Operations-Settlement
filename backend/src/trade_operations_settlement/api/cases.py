"""Case query and review snapshot presentation matching OpenAPI 3.1 contracts."""

from typing import Any

from trade_operations_settlement.application.tools.records import (
    CaseRecord,
    PolicyDecisionRecord,
    ProposalRecord,
)


def build_case_summary(case: CaseRecord) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "case_type": case.case_type,
        "status": case.state,
        "priority": case.priority,
        "counterparty_or_custodian": case.counterparty_or_custodian,
        "instrument": case.instrument_id,
        "currency": case.currency,
        "exposure_amount": str(case.exposure_amount),
        "deadline_at": case.deadline_at.isoformat() if case.deadline_at else None,
        "updated_at": case.updated_at.isoformat(),
    }


def build_case_review_snapshot(
    case: CaseRecord,
    policy_decision: PolicyDecisionRecord | None = None,
    proposal: ProposalRecord | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    snapshot = build_case_summary(case)
    snapshot["case_version"] = case.case_version
    snapshot["summary"] = f"{case.case_type} - {case.counterparty_or_custodian}"

    if policy_decision:
        snapshot["policy_decision"] = {
            "outcome": policy_decision.outcome,
            "reason_codes": policy_decision.reason_codes,
            "confidence": policy_decision.inputs_snapshot.get("confidence", "0.95"),
        }
    else:
        snapshot["policy_decision"] = None

    if proposal:
        snapshot["proposal"] = {
            "account_id": proposal.account_id,
            "direction": proposal.direction,
            "amount": str(proposal.amount),
            "currency": proposal.currency,
            "value_date": proposal.value_date,
            "reason_code": proposal.reason_code,
        }
    else:
        snapshot["proposal"] = None

    snapshot["evidence_citations"] = citations or []
    return snapshot
