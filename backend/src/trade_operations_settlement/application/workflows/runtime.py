"""PortAgent runtime adapter, allowlisted read-only tool registration, and workflow orchestration.

CRITICAL ARCHITECTURE INVARIANT:
PortAgent 0.0.2 is the application's SOLE agentic runtime and orchestration layer.
Agents receive only allowlisted read-only retrieval and screening tools.
Zero ledger-write or financial calculation tools are exposed to PortAgent agents.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from portagent.core.agent import AgentSpec
from portagent.core.response import AgentResponse
from portagent.core.state import AppState
from portagent.core.tool import (
    ToolDefinition,
    ToolExecutor,
)
from portagent.core.workflow import WorkflowDefinition, WorkflowEdge
from portagent.providers.registry import register_defaults
from portagent.runtime import wiring
from portagent.runtime.adapter_bootstrap import register_builtin_adapters
from portagent.runtime.context import RuntimeContext
from portagent.runtime.engine import RuntimeEngine

_log = logging.getLogger(__name__)

PROHIBITED_AGENT_TOOL_NAMES: set[str] = {
    "ledger_write",
    "post_transaction",
    "submit_ledger_entry",
    "mutate_account_balance",
    "execute_financial_transfer",
    "override_policy",
    "authorize_payment",
}


def _load_env_if_present() -> None:
    """Load repository root or local .env into os.environ if python-dotenv is available."""
    try:
        from dotenv import find_dotenv, load_dotenv

        dotenv_file = find_dotenv(usecwd=True)
        if dotenv_file:
            load_dotenv(dotenv_file, override=False)
        else:
            candidate = Path.cwd() / ".env"
            if candidate.exists():
                load_dotenv(candidate, override=False)
            elif (Path.cwd().parent / ".env").exists():
                load_dotenv(Path.cwd().parent / ".env", override=False)
    except Exception as exc:  # noqa: BLE001
        _log.debug("Dotenv load notice: %s", exc)


_load_env_if_present()


def resolve_runtime_settings(config_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve framework, model, and orchestration configuration from environment or overrides.

    Precedence:
    1. Caller config_overrides
    2. Environment variables (AI_PROVIDER / FRAMEWORK, OPENAI_MODEL / MODEL, ORCHESTRATION_MODE)
    3. Defaults: framework=openai, model=gpt-4.1, orchestration_mode=sequential
    """
    _load_env_if_present()
    framework = (os.getenv("AI_PROVIDER") or os.getenv("FRAMEWORK") or "openai").strip().lower()
    model = (os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-4.1").strip()
    orchestration_mode = os.getenv("ORCHESTRATION_MODE", "sequential").strip().lower()

    cfg: dict[str, Any] = {
        "framework": framework,
        "model": model,
        "orchestration_mode": orchestration_mode,
    }
    parallel_max_workers = os.getenv("PARALLEL_MAX_WORKERS")
    if parallel_max_workers:
        try:
            cfg["parallel_max_workers"] = int(parallel_max_workers)
        except ValueError:
            pass
    supervisor_agent_id = os.getenv("SUPERVISOR_AGENT_ID")
    if supervisor_agent_id:
        cfg["supervisor_agent_id"] = supervisor_agent_id.strip()

    if config_overrides:
        cfg.update(config_overrides)
    return cfg


class ProhibitedToolError(Exception):
    """Raised when an attempt is made to register a ledger write or mutative tool for an agent."""


class ReadOnlyToolCatalog:
    """Catalog of allowlisted read-only tools registered into PortAgent."""

    def __init__(self) -> None:
        self._registered_ids: set[str] = set()

    def register(self, definition: ToolDefinition, executor: ToolExecutor) -> None:
        if definition.id in PROHIBITED_AGENT_TOOL_NAMES:
            raise ProhibitedToolError(
                f"Tool '{definition.id}' is prohibited from agent registration: "
                "agents must not have ledger-write or financial calculation capability."
            )
        # Register into PortAgent singleton wiring
        wiring.register_tool(definition, executor)
        self._registered_ids.add(definition.id)

    def is_registered(self, tool_id: str) -> bool:
        return tool_id in self._registered_ids

    def all_ids(self) -> list[str]:
        return sorted(self._registered_ids)


class PortAgentRuntime:
    """Application-level runtime coordinator wrapping PortAgent 0.0.2 RuntimeEngine."""

    def __init__(self, catalog: ReadOnlyToolCatalog | None = None) -> None:
        self.catalog = catalog or ReadOnlyToolCatalog()
        self.engine = RuntimeEngine()
        self._initialized = False

    def initialize(
        self,
        config_path: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """Initialize PortAgent providers, adapters, and RuntimeEngine."""
        if not self._initialized:
            # 1. Register PortAgent default providers (OpenAI, Claude, Gemini, Azure)
            try:
                register_defaults()
            except Exception as e:  # noqa: BLE001
                _log.debug("Provider registration notice: %s", e)

            # 2. Resolve configured framework & model
            cfg = resolve_runtime_settings()
            resolved_model = model_name or cfg.get("model", "gpt-4.1")

            # 3. Register PortAgent built-in framework adapters
            try:
                register_builtin_adapters(model_name=resolved_model, config_path=config_path)
            except Exception as e:  # noqa: BLE001
                _log.debug("Adapters already registered or fallback: %s", e)

            # 4. Initialize PortAgent RuntimeEngine
            self.engine.initialize(config_path=config_path)
            self._initialized = True

    def verify_tool_safety(self) -> bool:
        """Assert that no mutative or ledger write tools are registered in PortAgent."""
        for tool_id in wiring.tool_ids():
            if tool_id in PROHIBITED_AGENT_TOOL_NAMES:
                return False
        return True

    def register_read_only_tool(self, definition: ToolDefinition, executor: ToolExecutor) -> None:
        """Register an allowlisted read-only tool for PortAgent agents."""
        self.catalog.register(definition, executor)

    def load_context(
        self,
        workflow: WorkflowDefinition | None = None,
        agents: list[AgentSpec] | None = None,
        config_overrides: dict[str, Any] | None = None,
    ) -> RuntimeContext:
        """Build execution context with framework and orchestration config overrides."""
        if not self._initialized:
            self.initialize()
        overrides = resolve_runtime_settings(config_overrides)
        return self.engine.load_context(
            workflow=workflow,
            agents=agents,
            config_overrides=overrides,
        )

    def run_workflow(
        self,
        workflow: WorkflowDefinition,
        agents: dict[str, AgentSpec],
        user_input: str,
        state: AppState | None = None,
        goal: str | None = None,
        config_overrides: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Execute a PortAgent workflow definition through RuntimeEngine."""
        self.load_context(
            workflow=workflow,
            agents=list(agents.values()),
            config_overrides=config_overrides,
        )

        # Run through PortAgent's RuntimeEngine
        return self.engine.run(
            workflow=workflow,
            agents=agents,
            user_input=user_input,
            state=state,
            goal=goal,
        )


__all__ = [
    "PROHIBITED_AGENT_TOOL_NAMES",
    "AgentResponse",
    "AgentSpec",
    "AppState",
    "PortAgentRuntime",
    "ProhibitedToolError",
    "ReadOnlyToolCatalog",
    "ToolDefinition",
    "ToolExecutor",
    "WorkflowDefinition",
    "WorkflowEdge",
    "resolve_runtime_settings",
]
