"""Override global PortAgent wiring with MCP proxy executors for Trade Operations tools.

Follows the reference common-sdk PortAgent MCP integration pattern:
- Call activate_mcp_tools() after local tools have been registered in wiring.
- If TRADE_OPS_MCP_ENDPOINT is set, it discovers tools from the MCP server
  and registers MCPProxyExecutors in portagent.runtime.wiring.
- If TRADE_OPS_MCP_ENDPOINT is not set, it is a no-op and local tools stay active.
"""

from __future__ import annotations

import dataclasses
import logging
import os

from portagent.protocols.mcp.proxy import MCPProxyExecutor
from portagent.protocols.mcp.registry import MCPRegistry, MCPServer
from portagent.protocols.mcp.transport import JSONRPCTransport
from portagent.runtime.wiring import register_tool

from trade_operations_settlement.application.tools.trade_retrieval import (
    CHAT_RETRIEVAL_DEF,
    CONFIRM_RETRIEVAL_DEF,
    EXCEPTION_RETRIEVAL_DEF,
)

_MCP_TIMEOUT_SECONDS = 60
_ALL_TRADE_DEFS = [
    CHAT_RETRIEVAL_DEF,
    CONFIRM_RETRIEVAL_DEF,
    EXCEPTION_RETRIEVAL_DEF,
]
_log = logging.getLogger(__name__)


def activate_mcp_tools(mcp_endpoint: str | None = None) -> None:
    """Optionally replace local tool executors in global wiring with MCPProxyExecutors."""
    endpoint = (mcp_endpoint or os.environ.get("TRADE_OPS_MCP_ENDPOINT", "")).rstrip("/")
    if not endpoint:
        _log.info("TRADE_OPS_MCP_ENDPOINT not set — Trade Operations tools running locally")
        return

    mcp_reg = MCPRegistry()
    mcp_reg.register(
        MCPServer(
            name="trade_ops",
            endpoint=endpoint,
            namespace="trade_ops",
            transport=JSONRPCTransport(),
        )
    )
    try:
        mcp_reg.discover("trade_ops")  # live tools/list via JSON-RPC
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "Trade Operations MCP server unreachable at %s — tools remain local: %s",
            endpoint,
            exc,
        )
        return

    for defn in _ALL_TRADE_DEFS:
        mcp_defn = dataclasses.replace(defn, timeout_seconds=_MCP_TIMEOUT_SECONDS)
        register_tool(mcp_defn, MCPProxyExecutor(f"trade_ops.{defn.id}", mcp_reg))

    _log.info(
        "Trade Operations tools now routed through MCP server at %s (timeout=%ds)",
        endpoint,
        _MCP_TIMEOUT_SECONDS,
    )
