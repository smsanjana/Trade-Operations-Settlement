"""Unit tests for PortAgent MCP integration and tool activation pattern."""

from unittest.mock import MagicMock, patch

from portagent.protocols.mcp.proxy import MCPProxyExecutor
from portagent.runtime import wiring

from trade_operations_settlement.application.tools.bootstrap_mcp import activate_mcp_tools
from trade_operations_settlement.application.tools.trade_retrieval import (
    register_trade_retrieval_tools,
)


def test_activate_mcp_tools_noop_when_endpoint_empty():
    # When endpoint is empty, local tools stay registered as standard executors
    register_trade_retrieval_tools()
    activate_mcp_tools(mcp_endpoint="")
    defn, execr = wiring.get_tool("tool_retrieve_chat")
    assert defn.id == "tool_retrieve_chat"
    # Not an MCPProxyExecutor
    assert not isinstance(execr, MCPProxyExecutor)


def test_activate_mcp_tools_replaces_with_proxy_when_endpoint_set():
    register_trade_retrieval_tools()
    # Mock MCPRegistry discover
    with patch("trade_operations_settlement.application.tools.bootstrap_mcp.MCPRegistry") as mock_reg_cls:
        mock_reg = MagicMock()
        mock_reg_cls.return_value = mock_reg
        activate_mcp_tools(mcp_endpoint="http://localhost:8100/mcp")

        # discover called on the trade_ops namespace
        mock_reg.discover.assert_called_once_with("trade_ops")

        _defn, execr = wiring.get_tool("tool_retrieve_chat")
        # In PortAgent, wiring.register_tool wraps the executor in a ToolExecutorEngine
        from portagent.tools.executor import ToolExecutorEngine
        assert isinstance(execr, ToolExecutorEngine)
        assert isinstance(execr._executor, MCPProxyExecutor)
        assert execr._executor._tool_id == "trade_ops.tool_retrieve_chat"
