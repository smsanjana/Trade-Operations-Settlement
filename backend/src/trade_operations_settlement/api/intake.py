"""Intake service: ingests, validates, and deduplicates settlement exception events."""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from trade_operations_settlement.application.tools.audit import AuditWriter
from trade_operations_settlement.application.tools.records import CaseRecord
from trade_operations_settlement.application.tools.state_store import (
    ControlStateStore,
)


@dataclass
class IntakeEventEnvelope:
    event_id: str
    source_system: str
    idempotency_key: str
    event_type: str
    payload: dict[str, Any]
    received_at: str | None = None


class IntakeService:
    def __init__(self, state_store: ControlStateStore, audit_writer: AuditWriter) -> None:
        self.state_store = state_store
        self.audit_writer = audit_writer

    def process_intake(self, envelope: IntakeEventEnvelope) -> CaseRecord:
        case, _ = self.process_intake_with_status(envelope)
        return case

    def process_intake_with_status(self, envelope: IntakeEventEnvelope) -> tuple[CaseRecord, bool]:
        # Check idempotency: if already ingested from this source system, return existing case
        existing_case_id = self.state_store._inbox.get((envelope.source_system, envelope.idempotency_key))
        if existing_case_id:
            existing_case = self.state_store.get_case(existing_case_id)
            if existing_case:
                self.audit_writer.record_event(
                    case_id=existing_case.case_id,
                    event_type="intake.deduplicated",
                    actor="intake_service",
                    details={
                        "event_id": envelope.event_id,
                        "source_system": envelope.source_system,
                        "idempotency_key": envelope.idempotency_key,
                    },
                )
                return existing_case, True

        payload = envelope.payload
        is_corporate_action = (
            envelope.event_type == "corporate_action.received"
            or "corporate" in envelope.event_type.lower()
            or payload.get("classification") in ("mandatory", "voluntary")
            or "mandatory_or_voluntary" in payload
        )

        deadline_at = None
        if is_corporate_action:
            case_type = payload.get("event_type", "Corporate Action")
            counterparty = (
                payload.get("counterparty_or_custodian")
                or payload.get("custodian")
                or payload.get("counterparty")
                or "UNKNOWN"
            )
            instrument = payload.get("instrument_id") or payload.get("instrument") or "UNKNOWN"
            currency = payload.get("currency", "USD")
            desk_id = payload.get("desk_id", "CA_DESK")
            amt = payload.get("amount") or payload.get("exposure_amount") or "0.00"
            exposure = Decimal(str(amt))
            workflow_type = "corporate_action"
            deadline_str = payload.get("deadline_at")
            if deadline_str:
                from datetime import datetime

                try:
                    deadline_at = datetime.fromisoformat(deadline_str)
                except (ValueError, TypeError):
                    deadline_at = None
        else:
            break_type = payload.get("break_type", "unsupported")
            case_type = break_type
            counterparty = payload.get("counterparty", "UNKNOWN")
            instrument = payload.get("instrument", "UNKNOWN")
            currency = payload.get("currency", "USD")
            desk_id = payload.get("desk_id", "DEFAULT")
            workflow_type = "trade_break"

            # Calculate exposure
            expected_amt = payload.get("expected_amount")
            booked_amt = payload.get("booked_amount")
            exposure = Decimal("0.00")
            if expected_amt is not None and booked_amt is not None:
                exposure = abs(Decimal(str(expected_amt)) - Decimal(str(booked_amt)))
            elif payload.get("exposure_amount"):
                exposure = Decimal(str(payload.get("exposure_amount")))

        case_id = f"CAS-{uuid.uuid4().hex[:8].upper()}"
        priority = "high" if exposure > Decimal("1000.00") else "normal"
        if is_corporate_action and payload.get("mandatory_or_voluntary") == "voluntary":
            priority = "high"

        orchestration_mode = str(payload.get("orchestration_mode", "sequential")).strip().lower()
        if orchestration_mode not in ("sequential", "parallel", "hierarchical"):
            orchestration_mode = "sequential"

        case = CaseRecord(
            case_id=case_id,
            case_version=1,
            case_type=case_type,
            state="received",
            priority=priority,
            counterparty_or_custodian=counterparty,
            instrument_id=instrument,
            currency=currency,
            exposure_amount=exposure,
            source_system=envelope.source_system,
            intake_idempotency_key=envelope.idempotency_key,
            desk_id=desk_id,
            workflow_type=workflow_type,
            deadline_at=deadline_at,
            orchestration_mode=orchestration_mode,
        )

        self.state_store.create_case(case)

        self.audit_writer.record_event(
            case_id=case_id,
            event_type="intake.received",
            actor="intake_service",
            details={
                "event_id": envelope.event_id,
                "source_system": envelope.source_system,
                "event_type": envelope.event_type,
                "case_type": case_type,
                "exposure": str(exposure),
                "orchestration_mode": orchestration_mode,
            },
        )

        return case, False
