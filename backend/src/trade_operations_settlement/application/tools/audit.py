"""Append-only audit writing with per-case sequence and cryptographic integrity chaining.

Enforces immutable sequence numbers and tamper-evident SHA-256 hash chaining.
"""

import hashlib
import json
import uuid
from typing import Any

from trade_operations_settlement.application.tools.records import (
    AuditEventRecord,
    utc_now,
)
from trade_operations_settlement.application.tools.state_store import ControlStateStore


class AuditIntegrityError(Exception):
    """Raised when an audit chain verification fails or tampering is detected."""


class AuditWriter:
    def __init__(self, state_store: ControlStateStore) -> None:
        self.state_store = state_store
        self._last_hashes: dict[str, str] = {}  # case_id -> last event hash

    def record_event(
        self,
        case_id: str,
        event_type: str,
        actor: str,
        details: dict[str, Any],
        correlation_id: str = "",
    ) -> AuditEventRecord:
        existing_events = self.state_store.get_audit_events(case_id)
        sequence_number = len(existing_events) + 1
        previous_hash = self._last_hashes.get(case_id, "GENESIS_ROOT")

        # Canonicalize details for hashing
        payload_bytes = json.dumps(details, sort_keys=True, default=str).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Chain hash: sha256(previous_hash + sequence + event_type + payload_hash)
        chain_input = f"{previous_hash}:{sequence_number}:{event_type}:{payload_hash}".encode()
        event_hash = hashlib.sha256(chain_input).hexdigest()
        self._last_hashes[case_id] = event_hash

        audit_record = AuditEventRecord(
            audit_event_id=f"AUD-{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            sequence_number=sequence_number,
            event_type=event_type,
            actor=actor,
            payload_hash=event_hash,
            correlation_id=correlation_id,
            details=details,
            occurred_at=utc_now(),
        )

        self.state_store.append_audit_event(audit_record)
        return audit_record

    def verify_chain(self, case_id: str) -> bool:
        events = self.state_store.get_audit_events(case_id)
        if not events:
            return True

        current_prev = "GENESIS_ROOT"
        for idx, event in enumerate(events, start=1):
            if event.sequence_number != idx:
                raise AuditIntegrityError(
                    f"Sequence gap in case {case_id}: expected {idx}, found {event.sequence_number}"
                )

            payload_bytes = json.dumps(event.details, sort_keys=True, default=str).encode("utf-8")
            payload_hash = hashlib.sha256(payload_bytes).hexdigest()
            chain_input = f"{current_prev}:{event.sequence_number}:{event.event_type}:{payload_hash}".encode()
            expected_hash = hashlib.sha256(chain_input).hexdigest()

            if event.payload_hash != expected_hash:
                raise AuditIntegrityError(
                    f"Audit chain verification failed at sequence {event.sequence_number} for case {case_id}"
                )
            current_prev = expected_hash

        return True
