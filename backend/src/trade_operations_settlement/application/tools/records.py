"""Ordinary typed Python dataclass records for Trade Operations & Settlement domain and control state.

Zero Pydantic dependencies - uses pure standard library dataclasses, Decimal, and datetime.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class CaseRecord:
    case_id: str
    source_system: str
    intake_idempotency_key: str
    case_type: str
    state: str
    source_event_id: str = ""
    workflow_type: str = "trade_break"
    case_version: int = 1
    desk_id: str = "DEFAULT"
    priority: str = "Normal"
    counterparty_or_custodian: str = ""
    instrument_id: str = ""
    currency: str = "USD"
    exposure_amount: Decimal = Decimal("0.00")
    correlation_id: str = ""
    deadline_at: datetime | None = None
    received_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    current_evidence_set_id: str | None = None
    current_proposal_id: str | None = None
    current_policy_decision_id: str | None = None
    failure_class: str | None = None
    failure_reason_codes: list[str] = field(default_factory=list)
    orchestration_mode: str = "sequential"


@dataclass
class EvidenceArtifactRecord:
    evidence_id: str
    content_hash: str
    source_name: str
    media_type: str
    retention_class: str
    region: str
    storage_reference: str = ""
    trust_classification: str = "untrusted"
    legal_hold: bool = False
    captured_at: datetime = field(default_factory=utc_now)


@dataclass
class EvidenceCaseLinkRecord:
    case_id: str
    evidence_id: str
    purpose: str
    locator: str
    is_screened: bool = False
    is_blocked: bool = False
    screening_metadata: dict[str, Any] = field(default_factory=dict)


EvidenceLinkRecord = EvidenceCaseLinkRecord


@dataclass
class EvidenceSetRecord:
    evidence_set_id: str
    case_id: str
    evidence_ids: list[str]
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class CitationRecord:
    citation_id: str
    evidence_id: str
    locator: str
    excerpt: str = ""


@dataclass
class AgentFindingRecord:
    finding_id: str
    agent_name: str
    field_name: str
    field_value: Any
    confidence: Decimal
    citations: list[CitationRecord] = field(default_factory=list)
    is_conflict: bool = False
    escalate_requested: bool = False


@dataclass
class DeterministicCalculationRecord:
    calculation_id: str
    calculation_type: str
    rule_version: str
    inputs: dict[str, Any]
    intermediate_steps: dict[str, Any]
    outputs: dict[str, Any]
    rounding_mode: str = "ROUND_HALF_UP"
    calculated_at: datetime = field(default_factory=utc_now)


@dataclass
class ProposalRecord:
    proposal_id: str
    case_id: str
    proposal_version: int
    account_id: str
    direction: str
    amount: Decimal
    currency: str
    value_date: str
    reason_code: str
    calculation_id: str | None = None
    evidence_set_id: str | None = None
    is_valid: bool = True
    invalidation_reasons: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class PolicyConfigurationRecord:
    policy_version: str
    desk_id: str
    confidence_threshold: Decimal
    auto_post_limit: Decimal
    dual_control_threshold: Decimal
    eligible_case_types: list[str]
    effective_from: datetime
    effective_to: datetime | None = None


@dataclass
class PolicyDecisionRecord:
    decision_id: str
    case_id: str
    policy_version: str
    outcome: str  # rejected, approval_required, dual_control_required, autonomous_authorized
    reason_codes: list[str]
    evaluated_at: datetime = field(default_factory=utc_now)
    inputs_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalDecisionRecord:
    decision_id: str
    approval_cycle_id: str
    approver_id: str
    action: str  # approve, amend, reject
    slot_number: int
    note: str = ""
    amended_amount: Decimal | None = None
    decided_at: datetime = field(default_factory=utc_now)


@dataclass
class ApprovalCycleRecord:
    approval_cycle_id: str
    case_id: str
    case_version: int
    proposal_id: str
    policy_decision_id: str
    required_approvals: int
    state: str = "pending"  # pending, satisfied, rejected, superseded
    decisions: list[ApprovalDecisionRecord] = field(default_factory=list)


@dataclass
class PostingInstructionRecord:
    instruction_id: str
    case_id: str
    proposal_id: str
    idempotency_key: str
    payload_hash: str
    classification: str  # autonomous, human_approved
    status: str = "created"  # created, dispatched, acknowledged, rejected, outcome_unknown, reconciling
    external_reference: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class PostingResultRecord:
    result_id: str
    instruction_id: str
    status: str
    external_reference: str | None = None
    acknowledgement_payload: dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=utc_now)


@dataclass
class AuditEventRecord:
    case_id: str
    sequence_number: int
    event_type: str
    actor: str
    payload_hash: str
    audit_event_id: str = ""
    correlation_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass
class OutboxRecord:
    event_id: str
    channel: str
    event_type: str
    payload: dict[str, Any]
    status: str = "pending"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class InboxRecord:
    source_system: str
    idempotency_key: str
    received_at: datetime = field(default_factory=utc_now)
    case_id: str | None = None
