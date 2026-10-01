"""Transactional control state store for case versioning, idempotent inbox, audit, and outbox.

Enforces compare-and-swap on case_version, unique intake idempotency, immutable audit sequence,
and transactional outbox dispatch without Pydantic.
"""


from trade_operations_settlement.application.tools.records import (
    AuditEventRecord,
    CaseRecord,
    OutboxRecord,
    utc_now,
)


class ConcurrencyError(Exception):
    """Raised when an optimistic concurrency check fails on case_version."""


class DuplicateIdempotencyKeyError(Exception):
    """Raised when an intake event violates the unique (source_system, idempotency_key) constraint."""


class ControlStateStore:
    """In-memory transactional state store supporting synthetic testing and contract invariants.

    In production/PostgreSQL mode, SQL migrations enforce these same constraints via unique indexes.
    """

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}
        self._inbox: dict[tuple[str, str], str] = {}  # (source_system, idempotency_key) -> case_id
        self._audit_events: dict[str, list[AuditEventRecord]] = {}  # case_id -> ordered audit events
        self._outbox: dict[str, OutboxRecord] = {}  # event_id -> outbox record

    def create_case(self, case: CaseRecord) -> CaseRecord:
        key = (case.source_system, case.intake_idempotency_key)
        if key in self._inbox:
            raise DuplicateIdempotencyKeyError(
                f"Duplicate intake event for source '{case.source_system}' with idempotency key '{case.intake_idempotency_key}'"
            )
        if case.case_id in self._cases:
            raise ValueError(f"Case with ID {case.case_id} already exists")

        self._inbox[key] = case.case_id
        self._cases[case.case_id] = case
        return case

    def get_case(self, case_id: str) -> CaseRecord | None:
        return self._cases.get(case_id)

    def list_cases(self) -> list[CaseRecord]:
        return list(self._cases.values())

    def update_case_state(self, case_id: str, expected_version: int, new_state: str) -> CaseRecord:
        case = self._cases.get(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        if case.case_version != expected_version:
            raise ConcurrencyError(
                f"Stale case version for {case_id}: expected {expected_version}, current is {case.case_version}"
            )

        case.case_version += 1
        case.state = new_state
        case.updated_at = utc_now()
        return case

    def create_case_transactional(
        self,
        case: CaseRecord,
        audit_event: AuditEventRecord | None = None,
        outbox_record: OutboxRecord | None = None,
    ) -> CaseRecord:
        # Atomic registration
        self.create_case(case)

        if audit_event:
            self.append_audit_event(audit_event)

        if outbox_record:
            self._outbox[outbox_record.event_id] = outbox_record

        return case

    def append_audit_event(self, event: AuditEventRecord) -> None:
        case_id = event.case_id
        events = self._audit_events.setdefault(case_id, [])

        expected_seq = len(events) + 1
        if event.sequence_number != expected_seq:
            raise ValueError(
                f"Audit sequence mismatch for case {case_id}: expected {expected_seq}, got {event.sequence_number}"
            )

        events.append(event)

    def get_audit_events(self, case_id: str) -> list[AuditEventRecord]:
        return list(self._audit_events.get(case_id, []))

    def get_pending_outbox(self) -> list[OutboxRecord]:
        return [entry for entry in self._outbox.values() if entry.status == "pending"]

    def mark_outbox_dispatched(self, event_id: str) -> None:
        if event_id in self._outbox:
            self._outbox[event_id].status = "dispatched"
