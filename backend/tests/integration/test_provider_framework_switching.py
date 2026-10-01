"""Integration tests for AI Provider & Framework switching and configuration.

Verifies:
1. Default AI provider and framework is OpenAI (gpt-4.1).
2. Environment configuration (.env.example, .gitignore, resolution).
3. PortAgent 0.0.2 is the orchestration and execution engine.
4. Framework switching between supported adapters (openai, semantic_kernel, langgraph)
   preserves workflow definitions and agent specifications unchanged.
5. Orchestration mode switching (sequential, parallel, hierarchical).
6. Tool safety invariants (no mutative tools allowed).
7. MCP remains strictly a tool protocol, not an AI framework.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from portagent.adapters.google_adk import GoogleADKAdapter
from portagent.adapters.langgraph import LangGraphAdapter
from portagent.adapters.openai_agents import OpenAIAgentsAdapter
from portagent.adapters.semantic_kernel import SemanticKernelAdapter
from portagent.core.workflow import WorkflowDefinition, WorkflowEdge
from portagent.runtime import wiring
from portagent.runtime.engine import RuntimeEngine

from trade_operations_settlement.application.agents.trade_break import (
    build_trade_break_agent_specs,
)
from trade_operations_settlement.application.tools.bootstrap_mcp import activate_mcp_tools
from trade_operations_settlement.application.workflows.runtime import (
    PortAgentRuntime,
    ProhibitedToolError,
    resolve_runtime_settings,
)


def _get_repo_root() -> Path:
    # backend/tests/integration/test_*.py -> backend -> repo_root
    return Path(__file__).resolve().parent.parent.parent.parent


def test_gitignore_excludes_env() -> None:
    """Verify .gitignore excludes .env."""
    root = _get_repo_root()
    gitignore_path = root / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist in repository root"
    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]
    assert ".env" in lines, ".gitignore must explicitly ignore .env"


def test_env_example_documents_all_required_variables() -> None:
    """Verify .env.example contains all required configuration keys without secrets."""
    root = _get_repo_root()
    example_path = root / ".env.example"
    assert example_path.exists(), ".env.example must exist in repository root"
    content = example_path.read_text(encoding="utf-8")

    required_vars = [
        "AI_PROVIDER=openai",
        "FRAMEWORK=openai",
        "OPENAI_API_KEY=",
        "OPENAI_MODEL=gpt-4.1",
        "ORCHESTRATION_MODE=sequential",
        "PARALLEL_MAX_WORKERS=4",
        "SUPERVISOR_AGENT_ID=supervisor",
        "TRADE_OPS_ENV=synthetic",
        "TRADE_OPS_MCP_ENDPOINT=",
    ]
    for var in required_vars:
        assert var in content, f".env.example must document {var}"


def test_default_runtime_resolution() -> None:
    """Verify default runtime settings resolve to OpenAI with gpt-4.1 and sequential mode."""
    with patch.dict(os.environ, {}, clear=False):
        # Clear specific env vars if set to test pure defaults
        os.environ.pop("AI_PROVIDER", None)
        os.environ.pop("FRAMEWORK", None)
        os.environ.pop("OPENAI_MODEL", None)
        os.environ.pop("MODEL", None)
        os.environ.pop("ORCHESTRATION_MODE", None)

        settings = resolve_runtime_settings()
        assert settings["framework"] == "openai"
        assert settings["model"] == "gpt-4.1"
        assert settings["orchestration_mode"] == "sequential"
        assert settings.get("parallel_max_workers") == 4
        assert settings.get("supervisor_agent_id") == "supervisor"


def test_runtime_resolution_with_overrides() -> None:
    """Verify resolve_runtime_settings respects custom environment and config overrides."""
    with patch.dict(
        os.environ,
        {
            "AI_PROVIDER": "langgraph",
            "OPENAI_MODEL": "gpt-4o",
            "ORCHESTRATION_MODE": "parallel",
            "PARALLEL_MAX_WORKERS": "8",
        },
    ):
        settings = resolve_runtime_settings()
        assert settings["framework"] == "langgraph"
        assert settings["model"] == "gpt-4o"
        assert settings["orchestration_mode"] == "parallel"
        assert settings["parallel_max_workers"] == 8

        # Overrides take precedence over environment
        overridden = resolve_runtime_settings({"framework": "crewai", "orchestration_mode": "hierarchical"})
        assert overridden["framework"] == "crewai"
        assert overridden["orchestration_mode"] == "hierarchical"


def test_orchestration_mode_propagation_to_portagent_engine() -> None:
    """Verify orchestration modes (sequential, parallel, hierarchical) propagate to RuntimeEngine."""
    runtime = PortAgentRuntime()
    runtime.initialize()

    wf = WorkflowDefinition(
        id="test_orchestration_wf",
        nodes=["break_classifier", "trade_evidence"],
        edges=[WorkflowEdge(source="break_classifier", target="trade_evidence", type="sequential")],
    )
    agents = list(build_trade_break_agent_specs().values())[:2]

    for mode in ["sequential", "parallel", "hierarchical"]:
        ctx = runtime.load_context(
            workflow=wf,
            agents=agents,
            config_overrides={"framework": "openai", "orchestration_mode": mode},
        )
        assert ctx.execution_mode == mode, f"Execution mode should be {mode}"
        assert isinstance(ctx.adapter, OpenAIAgentsAdapter)


def test_framework_switching_adapters() -> None:
    """Verify switching framework changes PortAgent adapter while preserving workflow & agent definitions."""
    runtime = PortAgentRuntime()
    runtime.initialize()

    wf = WorkflowDefinition(
        id="test_switch_wf",
        nodes=["break_classifier", "trade_evidence"],
        edges=[WorkflowEdge(source="break_classifier", target="trade_evidence", type="sequential")],
    )
    agent_specs = build_trade_break_agent_specs()
    agents = list(agent_specs.values())[:2]

    # 1. Switch to OpenAI
    ctx_openai = runtime.load_context(
        workflow=wf,
        agents=agents,
        config_overrides={"framework": "openai", "orchestration_mode": "sequential"},
    )
    assert isinstance(ctx_openai.adapter, OpenAIAgentsAdapter)

    # 2. Switch to Semantic Kernel
    ctx_sk = runtime.load_context(
        workflow=wf,
        agents=agents,
        config_overrides={"framework": "semantic_kernel", "orchestration_mode": "sequential"},
    )
    assert isinstance(ctx_sk.adapter, SemanticKernelAdapter)

    # 3. Switch to LangGraph
    ctx_lg = runtime.load_context(
        workflow=wf,
        agents=agents,
        config_overrides={"framework": "langgraph", "orchestration_mode": "sequential"},
    )
    assert isinstance(ctx_lg.adapter, LangGraphAdapter)

    # Invariant: Workflow definition and agent specifications remain identical
    assert wf.id == "test_switch_wf"
    assert len(wf.nodes) == 2
    assert agents[0].id == "break_classifier"
    assert agents[1].id == "trade_evidence"


def test_prohibited_mutative_tools_rejected() -> None:
    """Verify that mutative or ledger write tools are strictly rejected by PortAgentRuntime."""
    from portagent.core.tool import ToolDefinition

    runtime = PortAgentRuntime()

    def dummy_executor(_params: dict) -> dict:
        return {}

    prohibited_tool = ToolDefinition(
        id="ledger_write",
        description="Write directly to ledger",
    )

    try:
        runtime.register_read_only_tool(prohibited_tool, dummy_executor)
        assert False, "Should have raised ProhibitedToolError"
    except ProhibitedToolError as exc:
        assert "is prohibited from agent registration" in str(exc)

    assert runtime.verify_tool_safety() is True


def test_mcp_remains_tool_protocol_not_framework() -> None:
    """Verify MCP is configured via TRADE_OPS_MCP_ENDPOINT and registers tools, not adapters."""
    # When endpoint is empty, it runs in-process tools and does not crash or replace adapters
    with patch.dict(os.environ, {"TRADE_OPS_MCP_ENDPOINT": ""}):
        activate_mcp_tools()
        # PortAgent adapters remain framework adapters, not MCP
        adapter = wiring.get_adapter("openai")
        assert isinstance(adapter, OpenAIAgentsAdapter)


def test_runtime_config_endpoint_returns_clean_non_secret_config() -> None:
    """Verify GET /api/v1/config/runtime returns active framework/model and never exposes secrets."""
    from starlette.testclient import TestClient
    from trade_operations_settlement.api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/config/runtime")
    assert response.status_code == 200
    data = response.json()

    assert data["framework"] == "openai"
    assert data["framework_display"] == "OpenAI"
    assert data["model"] == "gpt-4.1"
    assert data["orchestration_mode"] == "sequential"
    assert "supported_orchestration_modes" in data
    assert "sequential" in data["supported_orchestration_modes"]
    assert "parallel" in data["supported_orchestration_modes"]
    assert "hierarchical" in data["supported_orchestration_modes"]

    # Security Invariant: API keys must NEVER be exposed
    raw_text = response.text.lower()
    assert "api_key" not in raw_text
    assert "sk-" not in raw_text


def test_runtime_config_reflects_environment_override() -> None:
    """Verify runtime config endpoint dynamically reflects environment configuration changes."""
    from starlette.testclient import TestClient
    from trade_operations_settlement.api.main import app

    client = TestClient(app)
    with patch.dict(
        os.environ,
        {
            "AI_PROVIDER": "langgraph",
            "OPENAI_MODEL": "gpt-4o",
            "ORCHESTRATION_MODE": "parallel",
        },
    ):
        response = client.get("/api/v1/config/runtime")
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "langgraph"
        assert data["framework_display"] == "LangGraph"
        assert data["model"] == "gpt-4o"
        assert data["orchestration_mode"] == "parallel"


def test_intake_preserves_selected_orchestration_mode() -> None:
    """Verify intake endpoint accepts and persists orchestration_mode in CaseRecord and response."""
    from starlette.testclient import TestClient
    from trade_operations_settlement.api.main import app, state_store

    client = TestClient(app)
    payload = {
        "event_id": "EVT-ORCH-001",
        "source_system": "MUREX",
        "idempotency_key": "IDEMP-ORCH-001",
        "event_type": "settlement.exception.received",
        "payload": {
            "break_type": "Fee mismatch",
            "counterparty": "Apex Clearing",
            "instrument": "US0378331005",
            "currency": "USD",
            "expected_amount": "1000.00",
            "booked_amount": "900.00",
            "orchestration_mode": "parallel",
        },
    }
    response = client.post("/api/v1/intake/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["orchestration_mode"] == "parallel"

    case = state_store.get_case(data["case_id"])
    assert case is not None
    assert case.orchestration_mode == "parallel"


def test_intake_rejects_invalid_orchestration_mode() -> None:
    """Verify intake endpoint rejects unrecognized orchestration modes with 422 Problem Details."""
    from starlette.testclient import TestClient
    from trade_operations_settlement.api.main import app

    client = TestClient(app)
    payload = {
        "event_id": "EVT-ORCH-BAD",
        "source_system": "MUREX",
        "idempotency_key": "IDEMP-ORCH-BAD",
        "event_type": "settlement.exception.received",
        "payload": {
            "break_type": "Fee mismatch",
            "counterparty": "Apex Clearing",
            "instrument": "US0378331005",
            "expected_amount": "1000.00",
            "booked_amount": "900.00",
            "orchestration_mode": "unsupported_mode",
        },
    }
    response = client.post("/api/v1/intake/events", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "orchestration_mode" in data.get("detail", "")

