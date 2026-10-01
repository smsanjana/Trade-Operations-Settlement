"""Bounded read-only retrieval tools registered into PortAgent.

Zero ledger-write or financial calculation capability is exposed to agents.
"""

from typing import Any

from portagent.core.tool import ToolDefinition
from portagent.runtime import wiring


class BoundedChatRetrievalExecutor:
    def execute(self, input_data: dict[str, Any]) -> Any:
        # Returns bounded chat messages
        return input_data.get("chat_thread", [])


class BoundedConfirmationRetrievalExecutor:
    def execute(self, input_data: dict[str, Any]) -> Any:
        return input_data.get("confirm_text", "")


class BoundedExceptionRetrievalExecutor:
    def execute(self, input_data: dict[str, Any]) -> Any:
        return input_data.get("exception_text", "")


CHAT_RETRIEVAL_DEF = ToolDefinition(
    id="tool_retrieve_chat",
    description="Retrieves bounded chat thread between trader and counterparty",
    input_schema={"type": "object"},
    output_schema={"type": "array"},
)

CONFIRM_RETRIEVAL_DEF = ToolDefinition(
    id="tool_retrieve_confirm",
    description="Retrieves trade confirmation electronic text",
    input_schema={"type": "object"},
    output_schema={"type": "string"},
)

EXCEPTION_RETRIEVAL_DEF = ToolDefinition(
    id="tool_retrieve_exception",
    description="Retrieves incoming settlement exception notice",
    input_schema={"type": "object"},
    output_schema={"type": "string"},
)


def register_trade_retrieval_tools() -> None:
    """Register allowlisted read-only retrieval tools into PortAgent singleton wiring."""
    tools = [
        (CHAT_RETRIEVAL_DEF, BoundedChatRetrievalExecutor()),
        (CONFIRM_RETRIEVAL_DEF, BoundedConfirmationRetrievalExecutor()),
        (EXCEPTION_RETRIEVAL_DEF, BoundedExceptionRetrievalExecutor()),
    ]

    for defn, executor in tools:
        wiring.register_tool(defn, executor)

