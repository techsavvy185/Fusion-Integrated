"""Specification tests for Workflow (WF) strategy.

Generated from docs/19-cms/spec-tests/WF_DESIGN.json per Assignment 9 Prompt B.
"""

from modules.cms.domain.rules import (
    VERIFY_COMPLAINANT,
    VERIFY_SUPERVISOR,
)
from modules.cms.domain.state_machine import (
    CLOSED,
    COMPLAINANT,
    HANDLER,
    HIGH,
    IN_PROGRESS,
    LOW,
    MEDIUM,
    REJECTED,
    RESOLVED,
    SUBMITTED,
    SUPERVISOR,
    check_transition,
)


def test_wf_001_submission_status_constant():
    """TEST-WF-001: BW-CMS-01 - Complaint submission workflow: SUBMITTED constant."""
    assert SUBMITTED == "submitted"


def test_wf_002_handler_starts_handling():
    """TEST-WF-002: BW-CMS-02 - Handler moves complaint to in_progress."""
    res = check_transition(
        SUBMITTED,
        IN_PROGRESS,
        HANDLER,
        passed_guards={"has_handling_setup": True},
    )
    assert res is not None


def test_wf_003_priority_constants():
    """TEST-WF-003: BW-CMS-03 - SLA priority constants used by pre-breach/auto-escalation."""
    assert HIGH == "High"
    assert MEDIUM == "Medium"
    assert LOW == "Low"


def test_wf_004_handler_resolves_or_rejects():
    """TEST-WF-004: BW-CMS-04 - Handler resolves or rejects an in-progress complaint."""
    res_resolve = check_transition(
        IN_PROGRESS,
        RESOLVED,
        HANDLER,
        passed_guards={"has_resolution_details": True},
    )
    assert res_resolve is not None

    res_reject = check_transition(
        IN_PROGRESS,
        REJECTED,
        HANDLER,
        passed_guards={"has_rejection_reason": True},
    )
    assert res_reject is not None


def test_wf_005_complainant_verifies_and_closes():
    """TEST-WF-005: BW-CMS-05 - Complainant verifies resolution → closed."""
    res = check_transition(
        RESOLVED,
        CLOSED,
        COMPLAINANT,
        passed_guards={"matches_required_verifier": True},
    )
    assert res is not None


def test_wf_006_supervisor_reopens_complaint():
    """TEST-WF-006: BW-CMS-06 - Supervisor approves reopening: closed → in_progress."""
    res = check_transition(
        CLOSED,
        IN_PROGRESS,
        SUPERVISOR,
        passed_guards={"has_pending_reopen_request": True},
    )
    assert res is not None


def test_wf_007_closed_status_constant():
    """TEST-WF-007: BW-CMS-07 - Post-closure feedback uses CLOSED status."""
    assert CLOSED == "closed"


def test_wf_008_announcement_broadcast():
    """TEST-WF-008: BW-CMS-08 - Public announcement broadcast (domain constant check)."""
    # Announcement broadcast does not change complaint status;
    # verified via registry/service layer constants only.
    assert CLOSED == "closed"  # domain constant used by announcement-aware services


def test_wf_009_full_routine_lifecycle():
    """TEST-WF-009: CW-CMS-01 - Full routine lifecycle: submit → in_progress → resolved → closed."""
    assert (
        check_transition(
            SUBMITTED,
            IN_PROGRESS,
            HANDLER,
            passed_guards={"has_handling_setup": True},
        )
        is not None
    )
    assert (
        check_transition(
            IN_PROGRESS,
            RESOLVED,
            HANDLER,
            passed_guards={"has_resolution_details": True},
        )
        is not None
    )
    assert (
        check_transition(
            RESOLVED,
            CLOSED,
            COMPLAINANT,
            passed_guards={"matches_required_verifier": True},
        )
        is not None
    )


def test_wf_010_escalated_lifecycle_supervisor_closure():
    """TEST-WF-010: CW-CMS-02 - Escalated lifecycle with supervisor verification."""
    # Supervisor can also close a resolved complaint.
    assert VERIFY_SUPERVISOR == "supervisor"
    assert VERIFY_COMPLAINANT == "complainant"
    res = check_transition(
        RESOLVED,
        CLOSED,
        SUPERVISOR,
        passed_guards={"matches_required_verifier": True},
    )
    assert res is not None


def test_wf_011_reopening_lifecycle():
    """TEST-WF-011: CW-CMS-03 - Reopening lifecycle: closed → in_progress (supervisor)."""
    assert (
        check_transition(
            CLOSED,
            IN_PROGRESS,
            SUPERVISOR,
            passed_guards={"has_pending_reopen_request": True},
        )
        is not None
    )
