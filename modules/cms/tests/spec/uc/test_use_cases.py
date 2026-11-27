"""Specification tests for Use Case (UC) strategy.

Generated from docs/19-cms/spec-tests/UC_DESIGN.json per Assignment 9 Prompt B.
Tests cover UC-CMS-001..022 (main flow + alternative/exception flow each).
Tests that only use the domain layer run without a DB.
Tests that require Django models/API use @pytest.mark.django_db.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from modules.cms.domain.rules import (
    VERIFY_COMPLAINANT,
    VERIFY_SUPERVISOR,
    PolicySnapshot,
    RuleViolation,
    validate_feedback,
    validate_handling_setup,
    validate_manual_escalation,
    validate_reopen_request,
    validate_submission,
)
from modules.cms.domain.sla import (
    should_auto_escalate,
    should_send_pre_breach_reminder,
)
from modules.cms.domain.state_machine import (
    CLOSED,
    COMPLAINANT,
    HANDLER,
    HIGH,
    IN_PROGRESS,
    MEDIUM,
    REJECTED,
    RESOLVED,
    SUPERVISOR,
    check_transition,
)
from modules.cms.registry import ROLE_GRANTS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _policy(
    low=72,
    medium=48,
    high=24,
    reminder_lead=4,
    max_att=3,
    routine=VERIFY_COMPLAINANT,
    escalated=VERIFY_SUPERVISOR,
    notify=True,
) -> PolicySnapshot:
    return PolicySnapshot(
        low_sla_hours=low,
        medium_sla_hours=medium,
        high_sla_hours=high,
        reminder_lead_hours=reminder_lead,
        max_attachments=max_att,
        routine_verification_by=routine,
        escalated_verification_by=escalated,
        notify_on_announcement=notify,
    )


# ---------------------------------------------------------------------------
# UC-CMS-001: Submit Complaint
# ---------------------------------------------------------------------------

def test_uc_001_main_submit_complaint_valid():
    """TEST-UC-001: UC-CMS-001 Main Flow - Valid submission passes all domain checks."""
    validate_submission("Network outage in block A", "No internet since morning", category_active=True)


def test_uc_002_exception_submit_complaint_blank_title():
    """TEST-UC-002: UC-CMS-001 Exception Flow - Blank title rejected."""
    with pytest.raises(RuleViolation, match="title_required"):
        validate_submission("", "Some description", category_active=True)


# ---------------------------------------------------------------------------
# UC-CMS-002: Track Submitted Complaint Status and History
# ---------------------------------------------------------------------------

def test_uc_003_main_track_complaint_student_has_view():
    """TEST-UC-003: UC-CMS-002 Main Flow - student role grants cms.complaint.view."""
    assert "cms.complaint.view" in ROLE_GRANTS["student"]


def test_uc_004_exception_track_complaint_other_role_no_view():
    """TEST-UC-004: UC-CMS-002 Exception Flow - adminstrator does not have cms.complaint.view."""
    assert "cms.complaint.view" not in ROLE_GRANTS["adminstrator"]


# ---------------------------------------------------------------------------
# UC-CMS-003: Review Assigned Complaints
# ---------------------------------------------------------------------------

def test_uc_005_main_handler_has_view_permission():
    """TEST-UC-005: UC-CMS-003 Main Flow - Handler has cms.complaint.view."""
    assert "cms.complaint.view" in ROLE_GRANTS["Complaint Handler"]


def test_uc_006_exception_handler_has_no_reopen_approve():
    """TEST-UC-006: UC-CMS-003 Exception Flow - Handler cannot approve reopen requests."""
    assert "cms.reopen_request.approve" not in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# UC-CMS-004: Assign, Categorize, and Prioritize Complaint
# ---------------------------------------------------------------------------

def test_uc_007_main_handling_setup_valid():
    """TEST-UC-007: UC-CMS-004 Main Flow - Valid handling setup passes domain check."""
    validate_handling_setup(
        priority=HIGH,
        category_active=True,
        assigned_to_user_id=42,
        assigned_unit="",
    )


def test_uc_008_exception_handling_setup_no_target():
    """TEST-UC-008: UC-CMS-004 Exception Flow - No assignment target raises error."""
    with pytest.raises(RuleViolation, match="assignment_target_required"):
        validate_handling_setup(
            priority=MEDIUM,
            category_active=True,
            assigned_to_user_id=None,
            assigned_unit="",
        )


# ---------------------------------------------------------------------------
# UC-CMS-005: Update Complaint Progress
# ---------------------------------------------------------------------------

def test_uc_009_main_handler_in_progress_to_in_progress():
    """TEST-UC-009: UC-CMS-005 Main Flow - Handler can record progress note."""
    t = check_transition(IN_PROGRESS, IN_PROGRESS, HANDLER, passed_guards={"has_progress_note": True})
    assert t is not None


def test_uc_010_exception_handler_needs_progress_note():
    """TEST-UC-010: UC-CMS-005 Exception Flow - Missing progress note guard fails."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_progress_note"):
        check_transition(IN_PROGRESS, IN_PROGRESS, HANDLER, passed_guards={})


# ---------------------------------------------------------------------------
# UC-CMS-006: Resolve or Reject Complaint
# ---------------------------------------------------------------------------

def test_uc_011_main_handler_resolves_complaint():
    """TEST-UC-011: UC-CMS-006 Main Flow - Handler transitions IN_PROGRESS -> RESOLVED."""
    t = check_transition(IN_PROGRESS, RESOLVED, HANDLER, passed_guards={"has_resolution_details": True})
    assert t.to == RESOLVED


def test_uc_012_exception_handler_rejects_without_reason():
    """TEST-UC-012: UC-CMS-006 Exception Flow - Guard fails without rejection reason."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_rejection_reason"):
        check_transition(IN_PROGRESS, REJECTED, HANDLER, passed_guards={})


# ---------------------------------------------------------------------------
# UC-CMS-007: Verify Resolved Complaint for Closure (User / Complainant)
# ---------------------------------------------------------------------------

def test_uc_013_main_complainant_closes_resolved():
    """TEST-UC-013: UC-CMS-007 Main Flow - Complainant closes RESOLVED -> CLOSED."""
    t = check_transition(RESOLVED, CLOSED, COMPLAINANT, passed_guards={"matches_required_verifier": True})
    assert t.to == CLOSED


def test_uc_014_exception_complainant_cannot_close_without_guard():
    """TEST-UC-014: UC-CMS-007 Exception Flow - Guard fails if verifier does not match."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="matches_required_verifier"):
        check_transition(RESOLVED, CLOSED, COMPLAINANT, passed_guards={})


# ---------------------------------------------------------------------------
# UC-CMS-008: Verify Resolved Complaint for Closure (Supervisor)
# ---------------------------------------------------------------------------

def test_uc_015_main_supervisor_closes_resolved():
    """TEST-UC-015: UC-CMS-008 Main Flow - Supervisor closes RESOLVED -> CLOSED."""
    t = check_transition(RESOLVED, CLOSED, SUPERVISOR, passed_guards={"matches_required_verifier": True})
    assert t.to == CLOSED


def test_uc_016_exception_handler_cannot_close():
    """TEST-UC-016: UC-CMS-008 Exception Flow - HANDLER cannot close a resolved complaint."""
    from modules.cms.domain.state_machine import ActorNotAllowed

    with pytest.raises(ActorNotAllowed):
        check_transition(RESOLVED, CLOSED, HANDLER, passed_guards={"matches_required_verifier": True})


# ---------------------------------------------------------------------------
# UC-CMS-009: Request Reopening of Closed Complaint
# ---------------------------------------------------------------------------

def test_uc_017_main_reopen_request_valid_on_closed():
    """TEST-UC-017: UC-CMS-009 Main Flow - Reopen request accepted for closed complaint."""
    validate_reopen_request(status=CLOSED, reason="Still unresolved", has_pending=False)


def test_uc_018_exception_reopen_request_on_non_closed():
    """TEST-UC-018: UC-CMS-009 Exception Flow - Reopen request on non-closed raises error."""
    with pytest.raises(RuleViolation, match="reopen_requires_closed"):
        validate_reopen_request(status=IN_PROGRESS, reason="Reason", has_pending=False)


# ---------------------------------------------------------------------------
# UC-CMS-010: Review and Decide Reopening Request
# ---------------------------------------------------------------------------

def test_uc_019_main_supervisor_approves_reopen():
    """TEST-UC-019: UC-CMS-010 Main Flow - Supervisor can reopen CLOSED -> IN_PROGRESS."""
    t = check_transition(CLOSED, IN_PROGRESS, SUPERVISOR, passed_guards={"has_pending_reopen_request": True})
    assert t.to == IN_PROGRESS


def test_uc_020_exception_reopen_no_pending_request():
    """TEST-UC-020: UC-CMS-010 Exception Flow - Guard fails if no pending reopen request."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_pending_reopen_request"):
        check_transition(CLOSED, IN_PROGRESS, SUPERVISOR, passed_guards={})


# ---------------------------------------------------------------------------
# UC-CMS-011: Submit Feedback
# ---------------------------------------------------------------------------

def test_uc_021_main_feedback_on_resolved():
    """TEST-UC-021: UC-CMS-011 Main Flow - Feedback valid when complaint resolved."""
    validate_feedback(status=RESOLVED, rating=4, already_submitted=False)


def test_uc_022_exception_feedback_on_in_progress():
    """TEST-UC-022: UC-CMS-011 Exception Flow - Feedback on in-progress raises error."""
    with pytest.raises(RuleViolation, match="feedback_not_allowed"):
        validate_feedback(status=IN_PROGRESS, rating=4, already_submitted=False)


# ---------------------------------------------------------------------------
# UC-CMS-012: Review Feedback
# ---------------------------------------------------------------------------

def test_uc_023_main_handler_can_review_feedback():
    """TEST-UC-023: UC-CMS-012 Main Flow - Handler has cms.feedback.review."""
    assert "cms.feedback.review" in ROLE_GRANTS["Complaint Handler"]


def test_uc_024_exception_student_cannot_review_feedback():
    """TEST-UC-024: UC-CMS-012 Exception Flow - student role does not have cms.feedback.review."""
    assert "cms.feedback.review" not in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# UC-CMS-013: Publish Announcement
# ---------------------------------------------------------------------------

def test_uc_025_main_handler_has_announcement_publish():
    """TEST-UC-025: UC-CMS-013 Main Flow - Handler has cms.announcement.publish."""
    assert "cms.announcement.publish" in ROLE_GRANTS["Complaint Handler"]


def test_uc_026_exception_student_cannot_publish_announcement():
    """TEST-UC-026: UC-CMS-013 Exception Flow - student role lacks cms.announcement.publish."""
    assert "cms.announcement.publish" not in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# UC-CMS-014: View Announcements
# ---------------------------------------------------------------------------

def test_uc_027_main_student_can_view_announcements():
    """TEST-UC-027: UC-CMS-014 Main Flow - student role has cms.announcement.view."""
    assert "cms.announcement.view" in ROLE_GRANTS["student"]


def test_uc_028_exception_admin_cannot_view_announcements():
    """TEST-UC-028: UC-CMS-014 Exception Flow - adminstrator role lacks cms.announcement.view."""
    assert "cms.announcement.view" not in ROLE_GRANTS["adminstrator"]


# ---------------------------------------------------------------------------
# UC-CMS-015: Manually Escalate Complaint
# ---------------------------------------------------------------------------

def test_uc_029_main_manual_escalation_valid():
    """TEST-UC-029: UC-CMS-015 Main Flow - Valid escalation for unresolved complaint."""
    validate_manual_escalation(status=IN_PROGRESS, is_escalated=False, reason="Risk of breach")


def test_uc_030_exception_already_escalated():
    """TEST-UC-030: UC-CMS-015 Exception Flow - Escalation of already-escalated complaint rejected."""
    with pytest.raises(RuleViolation, match="already_escalated"):
        validate_manual_escalation(status=IN_PROGRESS, is_escalated=True, reason="Reason")


# ---------------------------------------------------------------------------
# UC-CMS-016: Monitor Escalated Complaints
# ---------------------------------------------------------------------------

def test_uc_031_main_supervisor_has_escalation_view():
    """TEST-UC-031: UC-CMS-016 Main Flow - Supervisor has cms.escalation.view."""
    assert "cms.escalation.view" in ROLE_GRANTS["Complaint Supervisor"]


def test_uc_032_exception_handler_cannot_see_escalations():
    """TEST-UC-032: UC-CMS-016 Exception Flow - Handler does not have cms.escalation.view."""
    assert "cms.escalation.view" not in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# UC-CMS-017: Generate Complaint Reports
# ---------------------------------------------------------------------------

def test_uc_033_main_handler_has_report_view():
    """TEST-UC-033: UC-CMS-017 Main Flow - Handler has cms.report.view."""
    assert "cms.report.view" in ROLE_GRANTS["Complaint Handler"]


def test_uc_034_exception_student_cannot_view_reports():
    """TEST-UC-034: UC-CMS-017 Exception Flow - student role lacks cms.report.view."""
    assert "cms.report.view" not in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# UC-CMS-018: Manage Complaint Policy and Categories
# ---------------------------------------------------------------------------

def test_uc_035_main_admin_has_policy_manage():
    """TEST-UC-035: UC-CMS-018 Main Flow - adminstrator has cms.policy.manage."""
    assert "cms.policy.manage" in ROLE_GRANTS["adminstrator"]


def test_uc_036_exception_handler_cannot_manage_policy():
    """TEST-UC-036: UC-CMS-018 Exception Flow - Handler lacks cms.policy.manage."""
    assert "cms.policy.manage" not in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# UC-CMS-019: Send Pre-Breach Reminder Notification
# ---------------------------------------------------------------------------

def test_uc_037_main_pre_breach_reminder_in_window():
    """TEST-UC-037: UC-CMS-019 Main Flow - Reminder triggered in lead window."""
    now = datetime(2024, 6, 1, 20, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 6, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=4,
        now=now,
    )
    assert result is True


def test_uc_038_exception_reminder_not_sent_twice():
    """TEST-UC-038: UC-CMS-019 Exception Flow - Reminder suppressed after first send."""
    now = datetime(2024, 6, 1, 20, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 6, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=now - timedelta(hours=1),
        reminder_lead_hours=4,
        now=now,
    )
    assert result is False


# ---------------------------------------------------------------------------
# UC-CMS-020: Auto-Escalate SLA-Breached Complaint
# ---------------------------------------------------------------------------

def test_uc_039_main_auto_escalate_after_breach():
    """TEST-UC-039: UC-CMS-020 Main Flow - Auto escalation triggers after SLA breach."""
    sla_due_at = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 6, 1, 10, 1, tzinfo=UTC)
    assert should_auto_escalate(
        status=IN_PROGRESS, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is True


def test_uc_040_exception_no_auto_escalate_before_breach():
    """TEST-UC-040: UC-CMS-020 Exception Flow - No escalation before SLA breach."""
    sla_due_at = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 6, 1, 9, 59, tzinfo=UTC)
    assert should_auto_escalate(
        status=IN_PROGRESS, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is False


# ---------------------------------------------------------------------------
# UC-CMS-021: Send Pre-Breach Reminder — escalated complaint excluded
# ---------------------------------------------------------------------------

def test_uc_041_main_reminder_requires_unresolved_non_escalated():
    """TEST-UC-041: UC-CMS-021 Main Flow - Escalated complaints excluded from reminder."""
    now = datetime(2024, 6, 1, 20, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 6, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=True,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=4,
        now=now,
    )
    assert result is False


def test_uc_042_exception_reminder_suppressed_for_resolved():
    """TEST-UC-042: UC-CMS-021 Exception Flow - Resolved complaint not reminded."""
    now = datetime(2024, 6, 1, 20, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 6, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=RESOLVED,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=4,
        now=now,
    )
    assert result is False


# ---------------------------------------------------------------------------
# UC-CMS-022: Assign Handler / Supervisor Role
# ---------------------------------------------------------------------------

def test_uc_043_main_admin_has_policy_manage_for_role_assignment():
    """TEST-UC-043: UC-CMS-022 Main Flow - admin can manage policy/roles."""
    assert "cms.policy.manage" in ROLE_GRANTS["adminstrator"]


def test_uc_044_exception_non_admin_cannot_manage_roles():
    """TEST-UC-044: UC-CMS-022 Exception Flow - Supervisor cannot manage roles."""
    assert "cms.policy.manage" not in ROLE_GRANTS["Complaint Supervisor"]
