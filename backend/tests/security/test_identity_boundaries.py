"""Security tests for authentication, role boundaries, and actor permissions."""

import pytest

from trade_operations_settlement.api.security import (
    AccessDeniedError,
    AuthenticatedIdentity,
    Role,
    SecurityContext,
)


def test_analyst_identity_cannot_perform_final_approval_for_dual_control() -> None:
    analyst = AuthenticatedIdentity(
        user_id="analyst.1",
        roles={Role.SETTLEMENT_ANALYST},
        desk_id="EQUITIES_LON",
    )
    context = SecurityContext(analyst)
    # Analyst cannot perform approval
    assert not context.has_permission("case.approve")


def test_approver_identity_can_approve_within_desk() -> None:
    approver = AuthenticatedIdentity(
        user_id="supervisor.1",
        roles={Role.APPROVER},
        desk_id="EQUITIES_LON",
    )
    context = SecurityContext(approver)
    assert context.has_permission("case.approve")
    # But cannot cross desks if unauthorized
    assert not context.is_authorized_for_desk("FIXED_INCOME_NY")


def test_agent_identity_has_no_ledger_write_or_approval_path() -> None:
    agent = AuthenticatedIdentity(
        user_id="agent.break_classifier",
        roles={Role.AGENT},
        desk_id="SYSTEM",
    )
    context = SecurityContext(agent)
    assert not context.has_permission("ledger.write")
    assert not context.has_permission("case.approve")
    assert not context.has_permission("case.post")


def test_posting_service_identity_is_isolated() -> None:
    poster = AuthenticatedIdentity(
        user_id="service.posting_boundary",
        roles={Role.POSTING_SERVICE},
        desk_id="SYSTEM",
    )
    context = SecurityContext(poster)
    assert context.has_permission("ledger.write")
    # Posting service cannot approve cases
    assert not context.has_permission("case.approve")


def test_server_derived_identity_rejects_client_spoofed_approver() -> None:
    # Authenticated user is analyst.1
    caller = AuthenticatedIdentity(
        user_id="analyst.1",
        roles={Role.SETTLEMENT_ANALYST},
        desk_id="EQUITIES_LON",
    )
    context = SecurityContext(caller)
    with pytest.raises(AccessDeniedError):
        # Attempting to act as supervisor.1 must fail
        context.assert_can_act_as("supervisor.1")
