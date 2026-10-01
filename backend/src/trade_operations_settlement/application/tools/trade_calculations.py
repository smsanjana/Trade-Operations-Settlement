"""Deterministic trade arithmetic, SSI validation, and proposal construction.

CRITICAL INVARIANT:
Agents NEVER perform financial arithmetic or construct financial proposals.
All calculations use standard library Decimal with explicit rounding.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from trade_operations_settlement.application.tools.records import (
    ProposalRecord,
    utc_now,
)


def calculate_fee_difference(booked: Decimal, agreed: Decimal) -> Decimal:
    """Calculate fee/commission difference: agreed - booked."""
    diff = agreed - booked
    return diff.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_ssi_instructions(booked_ssi: dict[str, Any], agreed_ssi: dict[str, Any]) -> bool:
    """Validate standing settlement instructions match on critical fields."""
    critical_fields = ["account", "depository", "participant_id"]
    for field in critical_fields:
        if booked_ssi.get(field) != agreed_ssi.get(field):
            return False
    return True


def aggregate_weakest_confidence(confidences: list[Decimal]) -> Decimal:
    """Aggregate confidence by taking the weakest (minimum) link."""
    if not confidences:
        return Decimal("0.00")
    return min(confidences)


def build_amendment_proposal(
    case_id: str,
    account_id: str,
    difference_amount: Decimal,
    currency: str,
    value_date: str,
    reason_code: str,
    calculation_id: str | None = None,
    evidence_set_id: str | None = None,
) -> ProposalRecord:
    """Construct an immutable amendment proposal based strictly on deterministic calculation."""
    proposal_id = f"PROP-{uuid.uuid4().hex[:8].upper()}"
    direction = "credit" if difference_amount >= Decimal("0.00") else "debit"

    return ProposalRecord(
        proposal_id=proposal_id,
        case_id=case_id,
        proposal_version=1,
        account_id=account_id,
        direction=direction,
        amount=abs(difference_amount),
        currency=currency,
        value_date=value_date,
        reason_code=reason_code,
        calculation_id=calculation_id or f"CALC-{uuid.uuid4().hex[:8].upper()}",
        evidence_set_id=evidence_set_id or f"SET-{uuid.uuid4().hex[:8].upper()}",
        is_valid=True,
        created_at=utc_now(),
    )
