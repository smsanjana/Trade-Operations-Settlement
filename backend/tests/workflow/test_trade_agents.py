"""Workflow tests for PortAgent trade break agent specifications and interpreters."""

from decimal import Decimal

from portagent.core.agent import AgentSpec

from trade_operations_settlement.application.agents.trade_break import (
    BreakClassifierAgent,
    ChatConfirmReconciliationAgent,
    TradeEvidenceAgent,
    build_trade_break_agent_specs,
)


def test_agent_specs_are_valid_portagent_contracts():
    specs = build_trade_break_agent_specs()
    assert "break_classifier" in specs
    assert "trade_evidence" in specs
    assert "confirm_extractor" in specs
    assert "reconciler" in specs

    for agent_id, spec in specs.items():
        assert isinstance(spec, AgentSpec)
        assert spec.id == agent_id
        assert len(spec.role) > 0
        assert spec.prompt_ref.endswith(".md")


def test_break_classifier_agent_interprets_known_types():
    agent = BreakClassifierAgent()
    finding = agent.interpret("Settlement failed: Broker reports fee difference on LSE trade.")
    assert finding.field_value == "fee_break"
    assert finding.confidence >= Decimal("0.95")
    assert len(finding.citations) == 1


def test_trade_evidence_agent_preserves_chronology_supersession():
    agent = TradeEvidenceAgent()
    chat_thread = [
        {"msg_id": "M1", "sender": "Trader", "text": "Can we agree on fee 200.00 USD?"},
        {"msg_id": "M2", "sender": "Broker", "text": "No, desk approved fee of 250.00 USD"},
        {"msg_id": "M3", "sender": "Trader", "text": "Agreed, fee 250.00 USD confirmed."},
    ]
    finding = agent.interpret(chat_thread)
    assert finding.field_value["fee"] == "250.00"
    assert finding.is_conflict is False
    assert finding.confidence >= Decimal("0.90")


def test_reconciliation_detects_counterparty_dispute():
    reconciler = ChatConfirmReconciliationAgent()
    finding = reconciler.interpret(agreed_fee="250.00", confirm_fee="300.00")
    assert finding.is_conflict is True
    assert finding.escalate_requested is True
    assert finding.field_value["status"] == "COUNTERPARTY_DISPUTE"
