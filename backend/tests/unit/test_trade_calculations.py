"""Unit tests for deterministic trade arithmetic, SSI checks, and proposal construction."""

from decimal import Decimal

from trade_operations_settlement.application.tools.trade_calculations import (
    aggregate_weakest_confidence,
    build_amendment_proposal,
    calculate_fee_difference,
    validate_ssi_instructions,
)


def test_calculate_fee_difference():
    # booked: 12000.00, agreed: 12450.00 -> difference is 450.00
    diff = calculate_fee_difference(Decimal("12000.00"), Decimal("12450.00"))
    assert diff == Decimal("450.00")

    # Negative difference (over-booked)
    diff2 = calculate_fee_difference(Decimal("12500.00"), Decimal("12450.00"))
    assert diff2 == Decimal("-50.00")


def test_validate_ssi_instructions():
    booked_ssi = {"account": "ACC-01", "depository": "DTC", "participant_id": "0123"}
    agreed_ssi = {"account": "ACC-01", "depository": "DTC", "participant_id": "0123"}
    assert validate_ssi_instructions(booked_ssi, agreed_ssi) is True

    mismatch_ssi = {"account": "ACC-01", "depository": "EUROCLEAR", "participant_id": "9999"}
    assert validate_ssi_instructions(booked_ssi, mismatch_ssi) is False


def test_aggregate_weakest_confidence():
    confidences = [Decimal("0.99"), Decimal("0.95"), Decimal("0.98")]
    weakest = aggregate_weakest_confidence(confidences)
    assert weakest == Decimal("0.95")


def test_build_amendment_proposal():
    proposal = build_amendment_proposal(
        case_id="CAS-001",
        account_id="ACC-01",
        difference_amount=Decimal("450.00"),
        currency="GBP",
        value_date="2026-10-01",
        reason_code="FEE_DIFFERENCE",
    )
    assert proposal.case_id == "CAS-001"
    assert proposal.amount == Decimal("450.00")
    assert proposal.direction == "credit"
    assert proposal.is_valid is True
