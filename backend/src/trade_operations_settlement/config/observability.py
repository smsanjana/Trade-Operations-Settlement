"""Structured correlation logging, data masking, and operational metrics.

Ensures sensitive evidence and secrets are masked in logs, with full correlation across boundaries.
"""

import json
import logging
import re
from typing import Any

SENSITIVE_PATTERNS = [
    (re.compile(r"password", re.IGNORECASE), "******"),
    (re.compile(r"secret", re.IGNORECASE), "******"),
    (re.compile(r"token", re.IGNORECASE), "******"),
    (re.compile(r"account_number", re.IGNORECASE), "ACC-***MASKED***"),
]


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive keys and patterns in dictionaries/lists."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(p.search(str(k)) for p, _ in SENSITIVE_PATTERNS):
                masked[k] = "******"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data


class StructuredLogger:
    def __init__(self, name: str = "trade_operations_settlement") -> None:
        self.logger = logging.getLogger(name)

    def log(
        self,
        level: int,
        message: str,
        correlation_id: str = "",
        case_id: str = "",
        workflow_run_id: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "message": message,
            "correlation_id": correlation_id,
            "case_id": case_id,
            "workflow_run_id": workflow_run_id,
        }
        if extra:
            payload["details"] = mask_sensitive_data(extra)

        self.logger.log(level, json.dumps(payload, default=str))

    def info(self, message: str, **kwargs: Any) -> None:
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.log(logging.ERROR, message, **kwargs)


class OperationalMetrics:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {
            "autonomous_posted": 0,
            "human_approved": 0,
            "amended": 0,
            "rejected": 0,
            "conflicted": 0,
            "guardrail_blocked": 0,
            "reconciling": 0,
            "failed": 0,
        }

    def increment(self, outcome: str) -> None:
        if outcome in self.counters:
            self.counters[outcome] += 1
        else:
            self.counters[outcome] = self.counters.get(outcome, 0) + 1

    def get_metrics_snapshot(self) -> dict[str, int]:
        return dict(self.counters)
