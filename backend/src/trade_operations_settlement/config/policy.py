"""Effective-dated policy loading, validation, and fail-closed resolution.

Prohibits engineering defaults when policy configuration is missing, expired, or invalid.
"""

from datetime import UTC, datetime

from trade_operations_settlement.application.tools.records import (
    PolicyConfigurationRecord,
    utc_now,
)


class PolicyUnavailableError(Exception):
    """Raised when policy configuration is missing, expired, overlapping, or invalid."""


class PolicyRegistry:
    """Manages effective-dated, desk-scoped policy configurations."""

    def __init__(self) -> None:
        self._policies: dict[str, list[PolicyConfigurationRecord]] = {}  # desk_id -> list of policies

    def register_policy(self, config: PolicyConfigurationRecord) -> None:
        desk_policies = self._policies.setdefault(config.desk_id, [])

        # Validate no overlapping effective intervals for the same desk
        for existing in desk_policies:
            if self._intervals_overlap(
                config.effective_from, config.effective_to,
                existing.effective_from, existing.effective_to,
            ):
                raise PolicyUnavailableError(
                    f"Policy {config.policy_version} overlaps with {existing.policy_version} for desk {config.desk_id}"
                )

        desk_policies.append(config)

    def get_effective_policy(
        self,
        desk_id: str,
        as_of: datetime | None = None,
    ) -> PolicyConfigurationRecord:
        now = as_of or utc_now()
        desk_policies = self._policies.get(desk_id, [])

        # Check desk policies first, then fallback to DEFAULT desk if registered
        candidates = desk_policies or self._policies.get("DEFAULT", [])
        if not candidates:
            raise PolicyUnavailableError(
                f"No policy configuration found for desk '{desk_id}' (fails closed, no defaults permitted)"
            )

        for pol in candidates:
            if pol.effective_from <= now and (pol.effective_to is None or now < pol.effective_to):
                return pol

        raise PolicyUnavailableError(
            f"No active, unexpired policy configuration available for desk '{desk_id}' as of {now.isoformat()}"
        )

    @staticmethod
    def _intervals_overlap(
        start1: datetime, end1: datetime | None,
        start2: datetime, end2: datetime | None,
    ) -> bool:
        e1 = end1 or datetime.max.replace(tzinfo=UTC)
        e2 = end2 or datetime.max.replace(tzinfo=UTC)
        return max(start1, start2) < min(e1, e2)

