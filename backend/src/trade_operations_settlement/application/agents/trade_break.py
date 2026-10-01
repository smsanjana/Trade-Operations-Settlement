"""PortAgent-managed agents for trade break interpretation, evidence extraction, and chronology.

Agents declare AgentSpec contracts for PortAgent orchestration.
They interpret ambiguous evidence into structured findings with citations;
they do NOT perform financial arithmetic, policy decisions, or state mutation.
"""

import re
import uuid
from decimal import Decimal

from portagent.core.agent import AgentSpec

from trade_operations_settlement.application.tools.records import (
    AgentFindingRecord,
    CitationRecord,
)


def build_trade_break_agent_specs() -> dict[str, AgentSpec]:
    """Build framework-neutral PortAgent AgentSpec declarations for trade break resolution."""
    return {
        "break_classifier": AgentSpec(
            id="break_classifier",
            role="Classifies settlement exceptions into supported break types or unknown",
            tools=["tool_retrieve_exception"],
            prompt_ref="trade_break/break_classifier.v1.md",
        ),
        "trade_evidence": AgentSpec(
            id="trade_evidence",
            role="Interprets trader-broker communications, preserving chronology and supersession",
            tools=["tool_retrieve_chat"],
            prompt_ref="trade_break/trade_evidence.v1.md",
        ),
        "confirm_extractor": AgentSpec(
            id="confirm_extractor",
            role="Extracts economic terms from electronic confirmations and contract notes",
            tools=["tool_retrieve_confirm"],
            prompt_ref="trade_break/confirmation_extractor.v1.md",
        ),
        "reconciler": AgentSpec(
            id="reconciler",
            role="Reconciles chat and confirmation findings, detecting counterparty disputes",
            tools=[],
            prompt_ref="trade_break/reconciler.v1.md",
        ),
    }


class BreakClassifierAgent:
    """Interprets settlement break exceptions into supported categories."""

    def interpret(self, exception_text: str) -> AgentFindingRecord:
        txt = exception_text.lower()
        if "fee" in txt:
            b_type = "fee_break"
            conf = Decimal("0.98")
        elif "commission" in txt:
            b_type = "commission_break"
            conf = Decimal("0.97")
        elif "settlement" in txt and ("date" in txt or "value" in txt):
            b_type = "settlement_date_break"
            conf = Decimal("0.96")
        elif "ssi" in txt or "instruction" in txt:
            b_type = "ssi_break"
            conf = Decimal("0.95")
        else:
            b_type = "unknown"
            conf = Decimal("0.50")

        return AgentFindingRecord(
            finding_id=f"FND-{uuid.uuid4().hex[:8]}",
            agent_name="break_classifier",
            field_name="break_type",
            field_value=b_type,
            confidence=conf,
            citations=[
                CitationRecord(
                    citation_id=f"CIT-{uuid.uuid4().hex[:8]}",
                    evidence_id="EVD-INCOMING-EXCEPTION",
                    locator="field:exception_text",
                    excerpt=exception_text[:100],
                )
            ],
            is_conflict=(b_type == "unknown"),
            escalate_requested=(b_type == "unknown"),
        )


class TradeEvidenceAgent:
    """Interprets trader-broker chat, preserving chronology and supersession."""

    def interpret(self, chat_thread: list[dict[str, str]]) -> AgentFindingRecord:
        fee_val = None
        last_citation = None
        chronology_note = ""

        # Chronological evaluation: later statements supersede earlier ones
        for msg in chat_thread:
            txt = msg.get("text", "")
            match = re.search(
                r"fee\s*(is|of)?\s*(\d+(\.\d{2})?)|(\d+(\.\d{2})?)\s*(usd|gbp|eur)|agreed[^\d]*(\d+(\.\d{2})?)",
                txt,
                re.IGNORECASE,
            )
            if match:
                amt = match.group(2) or match.group(4) or match.group(7)
                if amt:
                    fee_val = f"{float(amt):.2f}"
                    last_citation = CitationRecord(
                        citation_id=f"CIT-{uuid.uuid4().hex[:8]}",
                        evidence_id="EVD-CHAT",
                        locator=f"msg_id:{msg.get('msg_id', 'unknown')}",
                        excerpt=txt,
                    )
                    chronology_note = f"Agreement in message {msg.get('msg_id')} supersedes previous terms."

        citations = [last_citation] if last_citation else []
        return AgentFindingRecord(
            finding_id=f"FND-{uuid.uuid4().hex[:8]}",
            agent_name="trade_evidence",
            field_name="agreed_terms",
            field_value={"fee": fee_val or "0.00", "chronology_note": chronology_note},
            confidence=Decimal("0.96") if fee_val else Decimal("0.40"),
            citations=citations,
            is_conflict=(fee_val is None),
        )


class ConfirmationExtractorAgent:
    """Extracts economic terms from electronic confirmation text."""

    def interpret(self, confirm_text: str) -> AgentFindingRecord:
        match = re.search(r"fee\s*(\d+(\.\d{2})?)", confirm_text, re.IGNORECASE)
        fee = f"{float(match.group(1)):.2f}" if match else None

        return AgentFindingRecord(
            finding_id=f"FND-{uuid.uuid4().hex[:8]}",
            agent_name="confirm_extractor",
            field_name="confirm_terms",
            field_value={"fee": fee or "0.00"},
            confidence=Decimal("0.98") if fee else Decimal("0.30"),
            citations=[
                CitationRecord(
                    citation_id=f"CIT-{uuid.uuid4().hex[:8]}",
                    evidence_id="EVD-CONFIRM",
                    locator="page:1",
                    excerpt=confirm_text[:100],
                )
            ],
            is_conflict=(fee is None),
        )


class ChatConfirmReconciliationAgent:
    """Reconciles chat and confirmation findings, detecting counterparty disputes."""

    def interpret(self, agreed_fee: str, confirm_fee: str) -> AgentFindingRecord:
        is_match = (agreed_fee.strip() == confirm_fee.strip())
        status = "AGREED" if is_match else "COUNTERPARTY_DISPUTE"

        return AgentFindingRecord(
            finding_id=f"FND-{uuid.uuid4().hex[:8]}",
            agent_name="reconciler",
            field_name="chat_confirm_reconciliation",
            field_value={
                "status": status,
                "agreed_fee": agreed_fee,
                "confirm_fee": confirm_fee,
            },
            confidence=Decimal("0.99"),
            is_conflict=not is_match,
            escalate_requested=not is_match,
        )
