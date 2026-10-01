"""ASGI application using Starlette with pure JSON Schema validation and zero Pydantic dependencies.

Provides authenticated case, evidence, audit, decision, and voluntary desk instruction endpoints.
"""

import os
from decimal import Decimal
from typing import Any

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from trade_operations_settlement.api.cases import build_case_review_snapshot, build_case_summary
from trade_operations_settlement.api.intake import IntakeEventEnvelope, IntakeService
from trade_operations_settlement.api.security import (
    AuthenticatedIdentity,
    Role,
    SecurityContext,
)
from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.evidence_store import EvidenceStore
from trade_operations_settlement.application.tools.records import (
    ApprovalCycleRecord,
    ApprovalDecisionRecord,
    AuditEventRecord,
    CaseRecord,
    PolicyDecisionRecord,
    ProposalRecord,
    utc_now,
)
from trade_operations_settlement.application.tools.state_store import (
    ConcurrencyError,
    ControlStateStore,
)
from trade_operations_settlement.application.workflows.runtime import (
    PortAgentRuntime,
    resolve_runtime_settings,
)

state_store = ControlStateStore()
evidence_store = EvidenceStore()
portagent_runtime = PortAgentRuntime()
portagent_runtime.initialize()
audit_writer = AuditWriter(state_store)
intake_service = IntakeService(state_store, audit_writer)

# Supplemental state for review snapshots and cycles
proposals: dict[str, ProposalRecord] = {}
policy_decisions: dict[str, PolicyDecisionRecord] = {}
approval_cycles: dict[str, ApprovalCycleRecord] = {}
evidence_links: dict[str, list[dict[str, Any]]] = {}


def seed_synthetic_fixtures() -> None:
    """Seed initial synthetic cases and associated evidence for local development/testing."""
    now = utc_now()

    # Case 1: Fee mismatch
    c1 = CaseRecord(
        case_id="TRD-28419",
        case_version=1,
        source_system="MUREX",
        intake_idempotency_key="INTAKE-TRD-28419",
        case_type="Fee mismatch",
        state="awaiting_approval",
        priority="High",
        counterparty_or_custodian="Northstar Securities",
        instrument_id="GB00B03MLX29",
        currency="GBP",
        exposure_amount=Decimal("450.00"),
        received_at=now,
        updated_at=now,
    )
    state_store.create_case(c1)
    proposals["TRD-28419"] = ProposalRecord(
        proposal_id="PROP-TRD-28419-1",
        case_id="TRD-28419",
        proposal_version=1,
        account_id="ACCT-7821",
        direction="Debit",
        amount=Decimal("450.00"),
        currency="GBP",
        value_date="2026-08-25",
        reason_code="FEE_CORRECTION",
    )
    policy_decisions["TRD-28419"] = PolicyDecisionRecord(
        decision_id="POL-TRD-28419-1",
        case_id="TRD-28419",
        policy_version="v1.0",
        outcome="approval_required",
        reason_codes=["Desk limit exceeded"],
        inputs_snapshot={"confidence": "0.97"},
    )
    evidence_links["TRD-28419"] = [
        {
            "evidence_id": "EV-CHAT-001",
            "source_name": "Trader-broker thread",
            "media_type": "text/plain",
            "retention_class": "STANDARD",
            "trust_classification": "untrusted",
            "locator": "Message 18",
            "excerpt": "Agreed final commission is GBP 12,450 for value date 25 Aug.",
        },
        {
            "evidence_id": "EV-CONF-001",
            "source_name": "Broker confirmation",
            "media_type": "application/pdf",
            "retention_class": "STANDARD",
            "trust_classification": "verified",
            "locator": "Page 2 - Fee summary",
            "excerpt": "Commission GBP 12,450.00; settlement date 25 August 2026.",
        },
    ]
    state_store.append_audit_event(
        AuditEventRecord(
            case_id="TRD-28419",
            sequence_number=1,
            event_type="intake.received",
            actor="intake_service",
            payload_hash="",
            audit_event_id="AUD-001",
            correlation_id="CORR-001",
        )
    )

    # Case 2: Cash dividend (awaiting second approval - dual control)
    c2 = CaseRecord(
        case_id="CA-77104",
        case_version=1,
        source_system="SWIFT",
        intake_idempotency_key="INTAKE-CA-77104",
        case_type="Cash dividend",
        state="awaiting_second_approval",
        priority="Critical",
        counterparty_or_custodian="Global Custody Bank",
        instrument_id="US0378331005",
        currency="USD",
        exposure_amount=Decimal("184250.00"),
        received_at=now,
        updated_at=now,
    )
    state_store.create_case(c2)
    proposals["CA-77104"] = ProposalRecord(
        proposal_id="PROP-CA-77104-1",
        case_id="CA-77104",
        proposal_version=1,
        account_id="OMNIBUS-US-03",
        direction="Credit",
        amount=Decimal("184250.00"),
        currency="USD",
        value_date="2026-09-04",
        reason_code="CASH_DIVIDEND",
    )
    policy_decisions["CA-77104"] = PolicyDecisionRecord(
        decision_id="POL-CA-77104-1",
        case_id="CA-77104",
        policy_version="v1.0",
        outcome="dual_control_required",
        reason_codes=["Dual-control threshold"],
        inputs_snapshot={"confidence": "0.99"},
    )
    evidence_links["CA-77104"] = [
        {
            "evidence_id": "EV-SWIFT-044",
            "source_name": "Custodian notice",
            "media_type": "text/plain",
            "retention_class": "STANDARD",
            "trust_classification": "verified",
            "locator": "Sequence D - Field 92A",
            "excerpt": "DIVR//USD1.25; PAYD//20260904",
        },
        {
            "evidence_id": "EV-ISSUER-044",
            "source_name": "Issuer announcement",
            "media_type": "text/plain",
            "retention_class": "STANDARD",
            "trust_classification": "verified",
            "locator": "Page 1",
            "excerpt": "Cash dividend USD 1.25 per share, payable 4 September 2026.",
        },
    ]
    # Record first approval by supervisor.a
    approval_cycles["CA-77104"] = ApprovalCycleRecord(
        approval_cycle_id="CYCLE-CA-77104-1",
        case_id="CA-77104",
        case_version=1,
        proposal_id="PROP-CA-77104-1",
        policy_decision_id="POL-CA-77104-1",
        required_approvals=2,
        state="pending",
        decisions=[
            ApprovalDecisionRecord(
                decision_id="DEC-CA-77104-1",
                approval_cycle_id="CYCLE-CA-77104-1",
                approver_id="supervisor.a",
                action="approve",
                slot_number=1,
                note="First control complete.",
            )
        ],
    )
    state_store.append_audit_event(
        AuditEventRecord(
            case_id="CA-77104",
            sequence_number=1,
            event_type="intake.received",
            actor="intake_service",
            payload_hash="",
            audit_event_id="AUD-002",
            correlation_id="CORR-002",
        )
    )

    # Case 3: Settlement date conflict
    c3 = CaseRecord(
        case_id="TRD-28431",
        case_version=1,
        source_system="TRAX",
        intake_idempotency_key="INTAKE-TRD-28431",
        case_type="Settlement date",
        state="awaiting_approval",
        priority="High",
        counterparty_or_custodian="Harbor Markets",
        instrument_id="DE0007164600",
        currency="EUR",
        exposure_amount=Decimal("7200.00"),
        received_at=now,
        updated_at=now,
    )
    state_store.create_case(c3)
    policy_decisions["TRD-28431"] = PolicyDecisionRecord(
        decision_id="POL-TRD-28431-1",
        case_id="TRD-28431",
        policy_version="v1.0",
        outcome="rejected",
        reason_codes=["Evidence conflict", "Confidence below threshold"],
        inputs_snapshot={"confidence": "0.72"},
    )
    evidence_links["TRD-28431"] = [
        {
            "evidence_id": "EV-CHAT-078",
            "source_name": "Trader-broker thread",
            "media_type": "text/plain",
            "retention_class": "STANDARD",
            "trust_classification": "untrusted",
            "locator": "Message 22",
            "excerpt": "Final settlement agreed for 28 August.",
        },
        {
            "evidence_id": "EV-CONF-078",
            "source_name": "Broker confirmation",
            "media_type": "text/plain",
            "retention_class": "STANDARD",
            "trust_classification": "verified",
            "locator": "Page 1",
            "excerpt": "Contractual settlement date: 29 August 2026.",
        },
    ]
    state_store.append_audit_event(
        AuditEventRecord(
            case_id="TRD-28431",
            sequence_number=1,
            event_type="intake.received",
            actor="intake_service",
            payload_hash="",
            audit_event_id="AUD-003",
            correlation_id="CORR-003",
        )
    )

    # Case 4: Stock split (auto-posted)
    c4 = CaseRecord(
        case_id="CA-77098",
        case_version=1,
        source_system="SWIFT",
        intake_idempotency_key="INTAKE-CA-77098",
        case_type="Stock split",
        state="posted",
        priority="Normal",
        counterparty_or_custodian="Atlas Custody",
        instrument_id="JP3435000009",
        currency="JPY",
        exposure_amount=Decimal("4980.00"),
        received_at=now,
        updated_at=now,
    )
    state_store.create_case(c4)
    proposals["CA-77098"] = ProposalRecord(
        proposal_id="PROP-CA-77098-1",
        case_id="CA-77098",
        proposal_version=1,
        account_id="TOKYO-OMNI-4",
        direction="Credit",
        amount=Decimal("4980.00"),
        currency="JPY",
        value_date="2026-08-22",
        reason_code="STOCK_SPLIT",
    )
    policy_decisions["CA-77098"] = PolicyDecisionRecord(
        decision_id="POL-CA-77098-1",
        case_id="CA-77098",
        policy_version="v1.0",
        outcome="autonomous_authorized",
        reason_codes=["Within approved autonomy"],
        inputs_snapshot={"confidence": "0.99"},
    )
    state_store.append_audit_event(
        AuditEventRecord(
            case_id="CA-77098",
            sequence_number=1,
            event_type="intake.received",
            actor="intake_service",
            payload_hash="",
            audit_event_id="AUD-004",
            correlation_id="CORR-004",
        )
    )
    state_store.append_audit_event(
        AuditEventRecord(
            case_id="CA-77098",
            sequence_number=2,
            event_type="posting.acknowledged",
            actor="posting-service",
            payload_hash="",
            audit_event_id="AUD-005",
            correlation_id="CORR-004",
        )
    )


# Automatically seed synthetic environment on boot if enabled
if os.environ.get("TRADE_OPS_ENV", "synthetic") == "synthetic":
    seed_synthetic_fixtures()


def problem_response(status: int, title: str, detail: str, type_uri: str = "about:blank") -> JSONResponse:
    """Return RFC 9457 compliant non-sensitive problem detail response."""
    return JSONResponse(
        status_code=status,
        content={
            "type": type_uri,
            "title": title,
            "status": status,
            "detail": detail,
        },
        headers={"Content-Type": "application/problem+json"},
    )


def resolve_security_context(request: Request) -> SecurityContext:
    """Derive authenticated actor identity from the server security context."""
    user_id = request.headers.get("x-user-id", "supervisor.test")
    role_str = request.headers.get("x-user-role", "supervisor")
    desk_id = request.headers.get("x-desk-id", "DEFAULT")

    try:
        role = Role(role_str)
    except ValueError:
        role = Role.APPROVER

    identity = AuthenticatedIdentity(
        user_id=user_id,
        roles={role},
        desk_id=desk_id,
    )
    return SecurityContext(identity)


async def health_check(request: Request) -> JSONResponse:
    is_safe = portagent_runtime.verify_tool_safety()
    return JSONResponse(
        {
            "status": "ok" if is_safe else "degraded",
            "dependencies": {
                "datastore": "operational",
                "evidence_store": "operational",
                "portagent_runtime": "operational" if is_safe else "unsafe_tools_detected",
            },
        }
    )


async def list_cases(request: Request) -> Response:
    cases = state_store.list_cases()

    # Query param filtering
    state_filter = request.query_params.get("state")
    priority_filter = request.query_params.get("priority")
    case_type_filter = request.query_params.get("case_type")

    if state_filter:
        cases = [c for c in cases if c.state == state_filter]
    if priority_filter:
        cases = [c for c in cases if c.priority.lower() == priority_filter.lower()]
    if case_type_filter:
        cases = [c for c in cases if c.case_type == case_type_filter]

    # Query param sorting
    sort_by = request.query_params.get("sort", "priority")
    if sort_by == "priority":
        p_rank = {"Critical": 0, "High": 1, "Normal": 2, "Low": 3}
        cases.sort(key=lambda c: p_rank.get(c.priority, 99))
    elif sort_by == "updated_at":
        cases.sort(key=lambda c: c.updated_at, reverse=True)

    items = [build_case_summary(c) for c in cases]
    return JSONResponse({"items": items, "next_cursor": None})


async def get_case(request: Request) -> Response:
    case_id = request.path_params.get("caseId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    snapshot = build_case_review_snapshot(
        case=case,
        policy_decision=policy_decisions.get(case_id),
        proposal=proposals.get(case_id),
        citations=evidence_links.get(case_id, []),
    )
    etag = f'"{case.case_id}-v{case.case_version}"'
    return JSONResponse(snapshot, headers={"ETag": etag})


async def list_case_evidence(request: Request) -> Response:
    case_id = request.path_params.get("caseId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    links = evidence_links.get(case_id, [])
    items = []
    for l in links:
        items.append(
            {
                "evidence_id": l["evidence_id"],
                "source_name": l["source_name"],
                "media_type": l["media_type"],
                "retention_class": l["retention_class"],
                "trust_classification": l["trust_classification"],
                "purpose": "reconciliation",
                "locator": l["locator"],
            }
        )
    return JSONResponse({"items": items, "next_cursor": None})


async def get_evidence_rendition(request: Request) -> Response:
    case_id = request.path_params.get("caseId", "")
    evidence_id = request.path_params.get("evidenceId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    links = evidence_links.get(case_id, [])
    target = next((l for l in links if l["evidence_id"] == evidence_id), None)
    if not target:
        return problem_response(
            404, "Not Found", f"Evidence '{evidence_id}' was not found for case '{case_id}'."
        )

    return JSONResponse(
        {
            "evidence_id": target["evidence_id"],
            "source_name": target["source_name"],
            "locator": target["locator"],
            "excerpt": target["excerpt"],
        }
    )


async def list_case_audit_events(request: Request) -> Response:
    case_id = request.path_params.get("caseId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    raw_events = state_store._audit_events.get(case_id, [])
    items = []
    for ev in raw_events:
        items.append(
            {
                "event_id": ev.audit_event_id or f"AUD-{ev.sequence_number}",
                "case_id": ev.case_id,
                "sequence_number": ev.sequence_number,
                "event_type": ev.event_type,
                "actor_identity": ev.actor,
                "actor_role": ev.details.get("role", "system"),
                "timestamp": ev.occurred_at.isoformat(),
            }
        )
    return JSONResponse({"items": items, "next_cursor": None})


async def record_decision(request: Request) -> Response:
    """Record an immutable approve, amend, or reject decision."""
    case_id = request.path_params.get("caseId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    # Concurrency verification via If-Match header
    if_match = request.headers.get("if-match")
    if not if_match:
        return problem_response(
            412,
            "Precondition Failed",
            "If-Match header is required for state-mutating decision commands.",
        )

    expected_etag = f'"{case.case_id}-v{case.case_version}"'
    if if_match != expected_etag and if_match != "*":
        return problem_response(
            409,
            "Conflict",
            f"Stale case version. Provided ETag '{if_match}' does not match current '{expected_etag}'.",
        )

    # Parse and validate JSON payload
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return problem_response(400, "Bad Request", "Malformed JSON body.")

    # Strict contract invariant: Decision requests must NOT contain client-authored approver identity
    if "approver_id" in body or "approverId" in body:
        return problem_response(
            422,
            "Unprocessable Content",
            "Decision requests must not provide client-authored approver identity.",
        )

    action = body.get("action")
    if action not in ("approve", "amend", "reject"):
        return problem_response(
            422,
            "Unprocessable Content",
            f"Invalid action '{action}'. Permitted actions are: approve, amend, reject.",
        )

    note = body.get("note", "").strip()
    if action in ("amend", "reject") and not note:
        return problem_response(
            422,
            "Unprocessable Content",
            f"Action '{action}' strictly requires a non-empty explanatory note.",
        )

    # Actor identity derived from authenticated security context
    security = resolve_security_context(request)
    actor_id = security.identity.user_id

    # Security boundary check: agents have zero decision authority
    if not security.has_permission(f"case.{action}"):
        return problem_response(
            403,
            "Forbidden",
            f"Actor '{actor_id}' with roles {[r.value for r in security.identity.roles]} is not authorized for '{action}'.",
        )

    # Dual control enforcement
    cycle = approval_cycles.get(case_id)
    if cycle and cycle.required_approvals > 1:
        # Check if this actor already approved in slot 1
        existing_approvers = [d.approver_id for d in cycle.decisions if d.action == "approve"]
        if actor_id in existing_approvers and action == "approve":
            return problem_response(
                409,
                "Conflict",
                f"Dual-control identity reuse prohibited: '{actor_id}' cannot provide a second approval for the same proposal.",
            )

    # Apply state transition
    next_state = case.state
    if action == "approve":
        if cycle and cycle.required_approvals > 1 and len(cycle.decisions) == 1:
            next_state = "posted"
            cycle.decisions.append(
                ApprovalDecisionRecord(
                    decision_id=f"DEC-{case_id}-{case.case_version + 1}",
                    approval_cycle_id=cycle.approval_cycle_id,
                    approver_id=actor_id,
                    action="approve",
                    slot_number=2,
                    note=note,
                )
            )
            cycle.state = "satisfied"
        elif cycle and cycle.required_approvals > 1:
            next_state = "awaiting_second_approval"
            cycle.decisions.append(
                ApprovalDecisionRecord(
                    decision_id=f"DEC-{case_id}-{case.case_version + 1}",
                    approval_cycle_id=cycle.approval_cycle_id,
                    approver_id=actor_id,
                    action="approve",
                    slot_number=1,
                    note=note,
                )
            )
        else:
            next_state = "posted"
    elif action == "amend":
        next_state = "awaiting_approval"
        amended_amt_str = body.get("amended_amount")
        if amended_amt_str:
            try:
                amended_amt = Decimal(str(amended_amt_str))
                prop = proposals.get(case_id)
                if prop:
                    prop.amount = amended_amt
                    prop.proposal_version += 1
            except (ArithmeticError, ValueError):
                return problem_response(422, "Unprocessable Content", "Invalid amended_amount.")
    elif action == "reject":
        next_state = "rejected"

    try:
        updated_case = state_store.update_case_state(
            case_id=case_id,
            expected_version=case.case_version,
            new_state=next_state,
        )
    except ConcurrencyError as e:
        return problem_response(409, "Conflict", str(e))

    # Append audit event
    seq = len(state_store._audit_events.get(case_id, [])) + 1
    state_store.append_audit_event(
        AuditEventRecord(
            case_id=case_id,
            sequence_number=seq,
            event_type=f"decision.{action}",
            actor=actor_id,
            payload_hash="",
            audit_event_id=f"AUD-{case_id}-{updated_case.case_version}",
            correlation_id=case.correlation_id or f"DEC-{case_id}",
            details={"role": next(iter(security.identity.roles)).value},
        )
    )

    new_snapshot = build_case_review_snapshot(
        case=updated_case,
        policy_decision=policy_decisions.get(case_id),
        proposal=proposals.get(case_id),
        citations=evidence_links.get(case_id, []),
    )
    new_etag = f'"{updated_case.case_id}-v{updated_case.case_version}"'
    return JSONResponse(new_snapshot, status_code=201, headers={"ETag": new_etag})


async def record_desk_instruction(request: Request) -> Response:
    """Record a human voluntary corporate action election; agent/service identities are rejected."""
    case_id = request.path_params.get("caseId", "")
    case = state_store.get_case(case_id)
    if not case:
        return problem_response(404, "Not Found", f"Case '{case_id}' was not found.")

    security = resolve_security_context(request)
    if not security.has_permission("voluntary.instruct"):
        return problem_response(
            403,
            "Forbidden",
            "Autonomous agents or unauthorized services are strictly forbidden from recording voluntary instructions.",
        )

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return problem_response(400, "Bad Request", "Malformed JSON body.")

    election = body.get("election")
    if not election:
        return problem_response(422, "Unprocessable Content", "Field 'election' is required.")

    updated_case = state_store.update_case_state(
        case_id=case_id,
        expected_version=case.case_version,
        new_state="instructed",
    )

    seq = len(state_store._audit_events.get(case_id, [])) + 1
    state_store.append_audit_event(
        AuditEventRecord(
            case_id=case_id,
            sequence_number=seq,
            event_type="voluntary.instructed",
            actor=security.identity.user_id,
            payload_hash="",
            audit_event_id=f"AUD-{case_id}-{updated_case.case_version}",
            correlation_id=case.correlation_id or f"VOL-{case_id}",
            details={"role": next(iter(security.identity.roles)).value},
        )
    )

    snapshot = build_case_review_snapshot(
        case=updated_case,
        policy_decision=policy_decisions.get(case_id),
        proposal=proposals.get(case_id),
        citations=evidence_links.get(case_id, []),
    )
    new_etag = f'"{updated_case.case_id}-v{updated_case.case_version}"'
    return JSONResponse(snapshot, status_code=201, headers={"ETag": new_etag})


async def submit_intake_event(request: Request) -> Response:
    """Submit an intake event through the application's intake boundary.

    Accepts an IntakeEventEnvelope matching AsyncAPI contracts.
    Preserves idempotency using (source_system, idempotency_key).
    """
    try:
        body = await request.json()
    except Exception:
        return problem_response(400, "Bad Request", "Malformed JSON body.")

    if not isinstance(body, dict):
        return problem_response(422, "Unprocessable Content", "Request body must be a JSON object.")

    source_system = body.get("source_system", "").strip()
    idempotency_key = body.get("idempotency_key", "").strip()
    event_type = body.get("event_type", "").strip()
    payload = body.get("payload")

    if not source_system:
        return problem_response(422, "Unprocessable Content", "Field 'source_system' is required.")
    if not idempotency_key:
        return problem_response(422, "Unprocessable Content", "Field 'idempotency_key' is required.")
    if not event_type:
        return problem_response(422, "Unprocessable Content", "Field 'event_type' is required.")
    if not isinstance(payload, dict):
        return problem_response(422, "Unprocessable Content", "Field 'payload' must be a JSON object.")

    # Validate permitted event types
    permitted_events = ("settlement.exception.received", "corporate_action.received")
    if event_type not in permitted_events:
        return problem_response(
            422,
            "Unprocessable Content",
            f"Invalid event_type '{event_type}'. Permitted event types: {list(permitted_events)}.",
        )

    # Validate orchestration_mode if provided
    if "orchestration_mode" in payload:
        mode = str(payload["orchestration_mode"]).strip().lower()
        if mode not in ("sequential", "parallel", "hierarchical"):
            return problem_response(
                422,
                "Unprocessable Content",
                "Field 'orchestration_mode' must be one of: sequential, parallel, hierarchical.",
            )

    # Validate payload fields
    if event_type == "settlement.exception.received":
        if not payload.get("break_type"):
            return problem_response(422, "Unprocessable Content", "Settlement exception payload requires 'break_type'.")
        if not payload.get("counterparty"):
            return problem_response(422, "Unprocessable Content", "Settlement exception payload requires 'counterparty'.")
        if not payload.get("instrument"):
            return problem_response(422, "Unprocessable Content", "Settlement exception payload requires 'instrument'.")
        if payload.get("expected_amount") is not None:
            try:
                Decimal(str(payload["expected_amount"]))
            except Exception:
                return problem_response(422, "Unprocessable Content", "Invalid 'expected_amount' format.")
        if payload.get("booked_amount") is not None:
            try:
                Decimal(str(payload["booked_amount"]))
            except Exception:
                return problem_response(422, "Unprocessable Content", "Invalid 'booked_amount' format.")
    elif event_type == "corporate_action.received":
        if not payload.get("event_type"):
            return problem_response(422, "Unprocessable Content", "Corporate action payload requires 'event_type'.")
        if payload.get("mandatory_or_voluntary") not in ("mandatory", "voluntary"):
            return problem_response(
                422,
                "Unprocessable Content",
                "Corporate action payload requires 'mandatory_or_voluntary' to be 'mandatory' or 'voluntary'.",
            )
        if payload.get("mandatory_or_voluntary") == "voluntary" and not payload.get("deadline_at"):
            return problem_response(
                422,
                "Unprocessable Content",
                "Voluntary corporate actions require 'deadline_at'.",
            )

    import uuid
    event_id = body.get("event_id") or f"EVT-{uuid.uuid4().hex[:8].upper()}"

    envelope = IntakeEventEnvelope(
        event_id=event_id,
        source_system=source_system,
        idempotency_key=idempotency_key,
        event_type=event_type,
        payload=payload,
    )

    case, deduplicated = intake_service.process_intake_with_status(envelope)

    # If newly created case, initialize review snapshot metadata so it is immediately reviewable in the console
    if not deduplicated:
        now_date = utc_now().strftime("%Y-%m-%d")
        reason_code = "BREAK_CORRECTION" if case.workflow_type == "trade_break" else "CORPORATE_ACTION"
        direction = "Credit" if "dividend" in case.case_type.lower() else "Debit"

        proposals[case.case_id] = ProposalRecord(
            proposal_id=f"PROP-{case.case_id}-1",
            case_id=case.case_id,
            proposal_version=1,
            account_id=payload.get("account_id", f"ACC-{case.desk_id}-01"),
            direction=direction,
            amount=case.exposure_amount,
            currency=case.currency,
            value_date=now_date,
            reason_code=reason_code,
        )

        outcome = "dual_control_required" if case.exposure_amount > Decimal("10000.00") else "approval_required"
        policy_decisions[case.case_id] = PolicyDecisionRecord(
            decision_id=f"POL-{case.case_id}-1",
            case_id=case.case_id,
            policy_version="v1.0",
            outcome=outcome,
            reason_codes=["Dual control threshold exceeded"] if outcome == "dual_control_required" else ["Review required by desk policy"],
            inputs_snapshot={"confidence": "0.95"},
        )

        # Register evidence snippets if provided in payload
        snippets = payload.get("evidence_snippets", [])
        if snippets and isinstance(snippets, list):
            evidence_links[case.case_id] = [
                {
                    "evidence_id": f"EV-{case.case_id}-{i+1}",
                    "source_name": s.get("source_name", "Source Evidence"),
                    "media_type": s.get("media_type", "text/plain"),
                    "retention_class": "STANDARD",
                    "trust_classification": "verified" if "confirm" in s.get("source_name", "").lower() else "untrusted",
                    "locator": s.get("locator", f"Snippet {i+1}"),
                    "excerpt": s.get("excerpt", ""),
                }
                for i, s in enumerate(snippets)
                if isinstance(s, dict) and s.get("excerpt")
            ]
        else:
            evidence_links[case.case_id] = [
                {
                    "evidence_id": f"EV-{case.case_id}-INTAKE",
                    "source_name": f"{case.source_system} Intake Feed",
                    "media_type": "application/json",
                    "retention_class": "STANDARD",
                    "trust_classification": "verified",
                    "locator": f"Event {event_id}",
                    "excerpt": f"Ingested {case.case_type} from {case.source_system} with exposure {case.currency} {case.exposure_amount}.",
                }
            ]

    status_code = 200 if deduplicated else 201
    return JSONResponse(
        {
            "case_id": case.case_id,
            "case_version": case.case_version,
            "case_type": case.case_type,
            "state": case.state,
            "priority": case.priority,
            "exposure_amount": str(case.exposure_amount),
            "currency": case.currency,
            "source_system": case.source_system,
            "idempotency_key": case.intake_idempotency_key,
            "orchestration_mode": getattr(case, "orchestration_mode", "sequential"),
            "deduplicated": deduplicated,
            "message": (
                f"Existing case '{case.case_id}' resolved via idempotency key '{idempotency_key}'."
                if deduplicated
                else f"Case '{case.case_id}' successfully created via intake boundary."
            ),
        },
        status_code=status_code,
    )


async def get_runtime_config(request: Request) -> JSONResponse:
    """Return active PortAgent AI framework, provider, and model runtime configuration.

    Zero secrets or API keys are exposed.
    """
    settings = resolve_runtime_settings()
    framework = settings.get("framework", "openai")
    model = settings.get("model", "gpt-4.1")
    orchestration_mode = settings.get("orchestration_mode", "sequential")

    display_names = {
        "openai": "OpenAI",
        "adk": "Google ADK",
        "langgraph": "LangGraph",
        "crewai": "CrewAI",
        "semantic_kernel": "Semantic Kernel",
    }
    framework_display = display_names.get(framework.lower(), framework.capitalize())

    return JSONResponse(
        {
            "framework": framework,
            "framework_display": framework_display,
            "provider": framework,
            "model": model,
            "orchestration_mode": orchestration_mode,
            "supported_orchestration_modes": ["sequential", "parallel", "hierarchical"],
            "environment": os.getenv("TRADE_OPS_ENV", "synthetic"),
            "mcp_enabled": bool(os.getenv("TRADE_OPS_MCP_ENDPOINT")),
        },
        status_code=200,
    )


# Build Starlette application
v1_routes = [
    Route("/cases", list_cases, methods=["GET"]),
    Route("/cases/{caseId}", get_case, methods=["GET"]),
    Route("/cases/{caseId}/evidence", list_case_evidence, methods=["GET"]),
    Route("/cases/{caseId}/evidence/{evidenceId}", get_evidence_rendition, methods=["GET"]),
    Route("/cases/{caseId}/audit-events", list_case_audit_events, methods=["GET"]),
    Route("/cases/{caseId}/decisions", record_decision, methods=["POST"]),
    Route("/cases/{caseId}/desk-instructions", record_desk_instruction, methods=["POST"]),
    Route("/intake/events", submit_intake_event, methods=["POST"]),
    Route("/config/runtime", get_runtime_config, methods=["GET"]),
    Route("/runtime/config", get_runtime_config, methods=["GET"]),
]

routes = [
    Route("/health", health_check, methods=["GET"]),
    Mount("/api/v1", routes=v1_routes),
]

app = Starlette(routes=routes)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
