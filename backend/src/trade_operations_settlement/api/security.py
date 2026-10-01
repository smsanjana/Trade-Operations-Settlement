"""Enterprise identity, role/desk/region authorization, and least-privilege security boundaries.

Prohibits client-supplied approver identities and enforces strict privilege segregation:
- Agents have zero ledger-write, approval, or posting capability.
- Posting service is isolated to governed posting only.
"""

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    SETTLEMENT_ANALYST = "settlement_analyst"
    CORPORATE_ACTIONS_ANALYST = "corporate_actions_analyst"
    APPROVER = "approver"
    SUPERVISOR = "supervisor"
    RISK_OWNER = "risk_owner"
    AUDITOR = "auditor"
    AGENT = "agent"
    POSTING_SERVICE = "posting_service"
    SYSTEM = "system"


class AccessDeniedError(Exception):
    """Raised when an actor attempts an action or impersonation outside granted permissions."""


# Strict capability allowlist per role
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.SETTLEMENT_ANALYST: {
        "case.read",
        "case.list",
        "evidence.read",
        "case.propose",
    },
    Role.CORPORATE_ACTIONS_ANALYST: {
        "case.read",
        "case.list",
        "evidence.read",
        "corporate_action.read",
        "voluntary.instruct",
    },
    Role.APPROVER: {
        "case.read",
        "case.list",
        "evidence.read",
        "case.approve",
        "case.amend",
        "case.reject",
    },
    Role.SUPERVISOR: {
        "case.read",
        "case.list",
        "evidence.read",
        "case.approve",
        "case.amend",
        "case.reject",
        "case.dual_control",
    },
    Role.RISK_OWNER: {
        "case.read",
        "case.list",
        "policy.read",
        "policy.manage",
        "audit.read",
        "evaluations.read",
    },
    Role.AUDITOR: {
        "case.read",
        "case.list",
        "audit.read",
        "evidence.metadata_only",
    },
    Role.AGENT: {
        # Strictly read-only / bounded interpretation; NO ledger write or approval
        "evidence.screened_read",
        "findings.produce",
    },
    Role.POSTING_SERVICE: {
        # Segregated posting boundary ONLY; NO approval or direct workflow modification
        "ledger.write",
        "posting.execute",
    },
    Role.SYSTEM: {
        "intake.process",
        "workflow.execute",
        "audit.append",
        "outbox.dispatch",
    },
}


@dataclass
class AuthenticatedIdentity:
    user_id: str
    roles: set[Role]
    desk_id: str = "DEFAULT"
    region: str = "GLOBAL"
    allowed_desks: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.desk_id and not self.allowed_desks:
            self.allowed_desks.add(self.desk_id)


class SecurityContext:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def has_permission(self, permission: str) -> bool:
        for role in self.identity.roles:
            perms = ROLE_PERMISSIONS.get(role, set())
            if permission in perms:
                return True
        return False

    def is_authorized_for_desk(self, desk_id: str) -> bool:
        if "GLOBAL" in self.identity.allowed_desks:
            return True
        return desk_id in self.identity.allowed_desks

    def assert_can_act_as(self, claimed_user_id: str) -> None:
        if claimed_user_id != self.identity.user_id:
            raise AccessDeniedError(
                f"Client claimed user_id '{claimed_user_id}' does not match authenticated identity '{self.identity.user_id}'"
            )
