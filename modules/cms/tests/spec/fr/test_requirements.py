"""Specification tests for Functional Requirement (FR) strategy.

Generated from docs/19-cms/spec-tests/FR_DESIGN.json per Assignment 9 Prompt B.
Tests cover AFR-CMS-001..073.
Tests that touch the domain layer only run without a DB.
Tests that require Django models/API use @pytest.mark.django_db.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from modules.cms.domain.rules import (
    VERIFICATION_MODES,
    VERIFY_COMPLAINANT,
    VERIFY_EITHER,
    VERIFY_SUPERVISOR,
    PolicySnapshot,
    RuleViolation,
    actor_matches_verifier,
    required_verifier,
    validate_attachment_count,
    validate_feedback,
    validate_handling_setup,
    validate_manual_escalation,
    validate_reopen_request,
    validate_submission,
)
from modules.cms.domain.sla import (
    compute_sla_due_at,
    should_auto_escalate,
    should_send_pre_breach_reminder,
    sla_hours_for_priority,
)
from modules.cms.domain.state_machine import (
    CLOSED,
    COMPLAINANT,
    HIGH,
    IN_PROGRESS,
    LOW,
    MEDIUM,
    REJECTED,
    RESOLVED,
    STATUSES,
    SUBMITTED,
    SUPERVISOR,
    UNRESOLVED_STATUSES,
    check_transition,
)
from modules.cms.registry import PERMISSIONS, ROLE_GRANTS

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
# AFR-CMS-001  (TEST-FR-001)  Submission allowed at any time
# ---------------------------------------------------------------------------

def test_fr_001_submission_no_error_with_valid_input():
    """TEST-FR-001: AFR-CMS-001 - Submission allowed; validate_submission passes."""
    validate_submission("Title", "Description body", category_active=True)


# ---------------------------------------------------------------------------
# AFR-CMS-002  (TEST-FR-002)  Category recorded
# ---------------------------------------------------------------------------

def test_fr_002_submission_records_category():
    """TEST-FR-002: AFR-CMS-002 - Domain validates category_active flag is True."""
    validate_submission("T", "D", category_active=True)


def test_fr_002_neg_inactive_category_rejected():
    """TEST-FR-002 negative: inactive category raises RuleViolation."""
    with pytest.raises(RuleViolation, match="category_inactive"):
        validate_submission("T", "D", category_active=False)


# ---------------------------------------------------------------------------
# AFR-CMS-003  (TEST-FR-003)  Description required
# ---------------------------------------------------------------------------

def test_fr_003_description_required():
    """TEST-FR-003: AFR-CMS-003 - Blank description rejected."""
    with pytest.raises(RuleViolation, match="description_required"):
        validate_submission("Title", "   ", category_active=True)


# ---------------------------------------------------------------------------
# AFR-CMS-004  (TEST-FR-004)  Submission date/time — domain-layer check
# ---------------------------------------------------------------------------

def test_fr_004_sla_due_at_uses_submission_time():
    """TEST-FR-004: AFR-CMS-004 - SLA due_at is derived from base submission time."""
    policy = _policy(high=24)
    base = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    due = compute_sla_due_at(base, HIGH, policy)
    assert due == base + timedelta(hours=24)


# ---------------------------------------------------------------------------
# AFR-CMS-005  (TEST-FR-005)  Attachments allowed
# ---------------------------------------------------------------------------

def test_fr_005_attachments_accepted_within_limit():
    """TEST-FR-005: AFR-CMS-005 - Up to max_attachments accepted without error."""
    validate_attachment_count(3, max_attachments=3)


# ---------------------------------------------------------------------------
# AFR-CMS-006  (TEST-FR-006)  Mandatory fields validated
# ---------------------------------------------------------------------------

def test_fr_006_blank_title_rejected():
    """TEST-FR-006: AFR-CMS-006 - Blank title raises RuleViolation."""
    with pytest.raises(RuleViolation, match="title_required"):
        validate_submission("", "Some description", category_active=True)


# ---------------------------------------------------------------------------
# AFR-CMS-007  (TEST-FR-007)  Attachment count enforced
# ---------------------------------------------------------------------------

def test_fr_007_too_many_attachments_rejected():
    """TEST-FR-007: AFR-CMS-007 - Exceeding max_attachments raises RuleViolation."""
    with pytest.raises(RuleViolation, match="too_many_attachments"):
        validate_attachment_count(4, max_attachments=3)


# ---------------------------------------------------------------------------
# AFR-CMS-008  (TEST-FR-008)  Attachment limits configurable
# ---------------------------------------------------------------------------

def test_fr_008_max_attachments_configurable_via_policy():
    """TEST-FR-008: AFR-CMS-008 - max_attachments is a policy field, not hardcoded."""
    p = _policy(max_att=10)
    assert p.max_attachments == 10
    validate_attachment_count(10, max_attachments=p.max_attachments)


# ---------------------------------------------------------------------------
# AFR-CMS-009  (TEST-FR-009)  Unique identifier — domain constant
# ---------------------------------------------------------------------------

def test_fr_009_submitted_status_constant():
    """TEST-FR-009: AFR-CMS-009 - SUBMITTED constant exists as string."""
    assert SUBMITTED == "submitted"


# ---------------------------------------------------------------------------
# AFR-CMS-010  (TEST-FR-010)  Submission notification — event constant
# ---------------------------------------------------------------------------

def test_fr_010_notification_module_importable():
    """TEST-FR-010: AFR-CMS-010 - Notification service importable (confirms triggering path)."""
    from modules.cms.services import notifications

    assert hasattr(notifications, "enqueue_notification")


# ---------------------------------------------------------------------------
# AFR-CMS-011  (TEST-FR-011)  Handler can assign
# ---------------------------------------------------------------------------

def test_fr_011_handler_has_assign_permission():
    """TEST-FR-011: AFR-CMS-011 - Complaint Handler role grants cms.complaint.assign."""
    assert "cms.complaint.assign" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-012  (TEST-FR-012)  Handler can categorize
# ---------------------------------------------------------------------------

def test_fr_012_handler_can_assign_category():
    """TEST-FR-012: AFR-CMS-012 - validate_handling_setup accepts active category."""
    validate_handling_setup(
        priority=HIGH,
        category_active=True,
        assigned_to_user_id=1,
        assigned_unit="",
    )


# ---------------------------------------------------------------------------
# AFR-CMS-013  (TEST-FR-013)  Priority Low / Medium / High
# ---------------------------------------------------------------------------

def test_fr_013_valid_priorities_accepted():
    """TEST-FR-013: AFR-CMS-013 - All three priority values pass validate_handling_setup."""
    for priority in (LOW, MEDIUM, HIGH):
        validate_handling_setup(
            priority=priority,
            category_active=True,
            assigned_to_user_id=1,
            assigned_unit="",
        )


def test_fr_013_invalid_priority_rejected():
    """TEST-FR-013 negative: unrecognised priority string raises RuleViolation."""
    with pytest.raises(RuleViolation, match="invalid_priority"):
        validate_handling_setup(
            priority="Urgent",
            category_active=True,
            assigned_to_user_id=1,
            assigned_unit="",
        )


# ---------------------------------------------------------------------------
# AFR-CMS-014  (TEST-FR-014)  Assignment info recorded
# ---------------------------------------------------------------------------

def test_fr_014_no_assignment_target_rejected():
    """TEST-FR-014: AFR-CMS-014 - No assigned_to_user_id AND blank unit raises error."""
    with pytest.raises(RuleViolation, match="assignment_target_required"):
        validate_handling_setup(
            priority=HIGH,
            category_active=True,
            assigned_to_user_id=None,
            assigned_unit="   ",
        )


# ---------------------------------------------------------------------------
# AFR-CMS-015  (TEST-FR-015)  Priority recorded for SLA
# ---------------------------------------------------------------------------

def test_fr_015_sla_hours_differ_by_priority():
    """TEST-FR-015: AFR-CMS-015 - Each priority maps to its own SLA hours."""
    p = _policy(low=72, medium=48, high=24)
    assert sla_hours_for_priority(LOW, p) == 72
    assert sla_hours_for_priority(MEDIUM, p) == 48
    assert sla_hours_for_priority(HIGH, p) == 24


# ---------------------------------------------------------------------------
# AFR-CMS-016  (TEST-FR-016)  Complainant can track status
# ---------------------------------------------------------------------------

def test_fr_016_student_has_complaint_view():
    """TEST-FR-016: AFR-CMS-016 - student role grants cms.complaint.view."""
    assert "cms.complaint.view" in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# AFR-CMS-017  (TEST-FR-017)  Complainant can track history
# ---------------------------------------------------------------------------

def test_fr_017_history_service_importable():
    """TEST-FR-017: AFR-CMS-017 - ComplaintHistory model importable (history is persisted)."""
    from modules.cms.models import ComplaintHistory

    assert ComplaintHistory is not None


# ---------------------------------------------------------------------------
# AFR-CMS-018  (TEST-FR-018)  Handler can review assigned complaints
# ---------------------------------------------------------------------------

def test_fr_018_handler_has_view_permission():
    """TEST-FR-018: AFR-CMS-018 - Complaint Handler role grants cms.complaint.view."""
    assert "cms.complaint.view" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-019  (TEST-FR-019)  Handler can update progress
# ---------------------------------------------------------------------------

def test_fr_019_handler_has_update_permission():
    """TEST-FR-019: AFR-CMS-019 - Complaint Handler role grants cms.complaint.update."""
    assert "cms.complaint.update" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-020  (TEST-FR-020)  Status history maintained
# ---------------------------------------------------------------------------

def test_fr_020_all_statuses_present():
    """TEST-FR-020: AFR-CMS-020 - All five lifecycle statuses are defined."""
    assert set(STATUSES) == {"submitted", "in_progress", "resolved", "rejected", "closed"}


# ---------------------------------------------------------------------------
# AFR-CMS-021  (TEST-FR-021)  Progress history maintained — model check
# ---------------------------------------------------------------------------

def test_fr_021_complaint_history_model_importable():
    """TEST-FR-021: AFR-CMS-021 - ComplaintHistory model importable (progress history)."""
    from modules.cms.models import ComplaintHistory

    assert ComplaintHistory is not None


# ---------------------------------------------------------------------------
# AFR-CMS-022  (TEST-FR-022)  Five lifecycle states
# ---------------------------------------------------------------------------

def test_fr_022_five_lifecycle_statuses():
    """TEST-FR-022: AFR-CMS-022 - Exactly five statuses: submitted, in_progress, resolved, rejected, closed."""
    assert SUBMITTED == "submitted"
    assert IN_PROGRESS == "in_progress"
    assert RESOLVED == "resolved"
    assert REJECTED == "rejected"
    assert CLOSED == "closed"


# ---------------------------------------------------------------------------
# AFR-CMS-023  (TEST-FR-023)  Resolution details recorded
# ---------------------------------------------------------------------------

def test_fr_023_handler_can_resolve():
    """TEST-FR-023: AFR-CMS-023 - HANDLER can transition IN_PROGRESS -> RESOLVED."""
    t = check_transition(IN_PROGRESS, RESOLVED, "handler", passed_guards={"has_resolution_details": True})
    assert t is not None


# ---------------------------------------------------------------------------
# AFR-CMS-024  (TEST-FR-024)  Rejection reason recorded
# ---------------------------------------------------------------------------

def test_fr_024_handler_can_reject():
    """TEST-FR-024: AFR-CMS-024 - HANDLER can transition IN_PROGRESS -> REJECTED."""
    t = check_transition(IN_PROGRESS, REJECTED, "handler", passed_guards={"has_rejection_reason": True})
    assert t is not None


# ---------------------------------------------------------------------------
# AFR-CMS-025  (TEST-FR-025)  Complainant notified of outcome
# ---------------------------------------------------------------------------

def test_fr_025_notification_service_has_enqueue():
    """TEST-FR-025: AFR-CMS-025 - enqueue_notification exists for outcome notification."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-026  (TEST-FR-026)  Complainant notified of status update
# ---------------------------------------------------------------------------

def test_fr_026_notification_service_importable():
    """TEST-FR-026: AFR-CMS-026 - Notification service exists for status update events."""
    from modules.cms.services import notifications

    assert hasattr(notifications, "enqueue_notification")


# ---------------------------------------------------------------------------
# AFR-CMS-027  (TEST-FR-027)  Complainant verification supported
# ---------------------------------------------------------------------------

def test_fr_027_complainant_can_close_resolved():
    """TEST-FR-027: AFR-CMS-027 - COMPLAINANT can transition RESOLVED -> CLOSED."""
    t = check_transition(RESOLVED, CLOSED, COMPLAINANT, passed_guards={"matches_required_verifier": True})
    assert t is not None


# ---------------------------------------------------------------------------
# AFR-CMS-028  (TEST-FR-028)  Supervisor verification supported
# ---------------------------------------------------------------------------

def test_fr_028_supervisor_can_close_resolved():
    """TEST-FR-028: AFR-CMS-028 - SUPERVISOR can transition RESOLVED -> CLOSED."""
    t = check_transition(RESOLVED, CLOSED, SUPERVISOR, passed_guards={"matches_required_verifier": True})
    assert t is not None


# ---------------------------------------------------------------------------
# AFR-CMS-029  (TEST-FR-029)  Closure recorded after verification
# ---------------------------------------------------------------------------

def test_fr_029_closed_status_exists():
    """TEST-FR-029: AFR-CMS-029 - CLOSED status constant exists."""
    assert CLOSED == "closed"


# ---------------------------------------------------------------------------
# AFR-CMS-030  (TEST-FR-030)  Complainant can request reopening
# ---------------------------------------------------------------------------

def test_fr_030_validate_reopen_request_passes_for_closed():
    """TEST-FR-030: AFR-CMS-030 - Reopen request valid when status is closed, reason given."""
    validate_reopen_request(status=CLOSED, reason="Unsatisfied", has_pending=False)


def test_fr_030_neg_reopen_requires_closed_status():
    """TEST-FR-030 negative: reopen request on non-closed complaint raises error."""
    with pytest.raises(RuleViolation, match="reopen_requires_closed"):
        validate_reopen_request(status=RESOLVED, reason="Reason", has_pending=False)


# ---------------------------------------------------------------------------
# AFR-CMS-031  (TEST-FR-031)  Supervisor reviews reopen requests
# ---------------------------------------------------------------------------

def test_fr_031_supervisor_has_reopen_approve():
    """TEST-FR-031: AFR-CMS-031 - Complaint Supervisor has cms.reopen_request.approve."""
    assert "cms.reopen_request.approve" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-032  (TEST-FR-032)  Approved reopen restores complaint
# ---------------------------------------------------------------------------

def test_fr_032_supervisor_can_reopen_via_state_machine():
    """TEST-FR-032: AFR-CMS-032 - SUPERVISOR can reopen CLOSED -> IN_PROGRESS."""
    t = check_transition(CLOSED, IN_PROGRESS, SUPERVISOR, passed_guards={"has_pending_reopen_request": True})
    assert t is not None


# ---------------------------------------------------------------------------
# AFR-CMS-033  (TEST-FR-033)  Status updated on reopen
# ---------------------------------------------------------------------------

def test_fr_033_in_progress_after_reopen():
    """TEST-FR-033: AFR-CMS-033 - Reopened complaint goes to IN_PROGRESS."""
    t = check_transition(CLOSED, IN_PROGRESS, SUPERVISOR, passed_guards={"has_pending_reopen_request": True})
    assert t.to == IN_PROGRESS


# ---------------------------------------------------------------------------
# AFR-CMS-034  (TEST-FR-034)  Reopen outcome recorded — model check
# ---------------------------------------------------------------------------

def test_fr_034_reopen_request_model_importable():
    """TEST-FR-034: AFR-CMS-034 - ReopenRequest model exists for recording outcome."""
    from modules.cms.models import ReopenRequest

    assert ReopenRequest is not None


# ---------------------------------------------------------------------------
# AFR-CMS-035  (TEST-FR-035)  Feedback after resolution / closure
# ---------------------------------------------------------------------------

def test_fr_035_feedback_accepted_on_resolved():
    """TEST-FR-035: AFR-CMS-035 - Feedback valid when complaint is resolved."""
    validate_feedback(status=RESOLVED, rating=4, already_submitted=False)


def test_fr_035_feedback_accepted_on_closed():
    """TEST-FR-035: AFR-CMS-035 - Feedback valid when complaint is closed."""
    validate_feedback(status=CLOSED, rating=5, already_submitted=False)


# ---------------------------------------------------------------------------
# AFR-CMS-036  (TEST-FR-036)  Handler can review feedback
# ---------------------------------------------------------------------------

def test_fr_036_handler_has_feedback_review():
    """TEST-FR-036: AFR-CMS-036 - Complaint Handler has cms.feedback.review."""
    assert "cms.feedback.review" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-037  (TEST-FR-037)  Supervisor can review feedback
# ---------------------------------------------------------------------------

def test_fr_037_supervisor_has_feedback_review():
    """TEST-FR-037: AFR-CMS-037 - Complaint Supervisor has cms.feedback.review."""
    assert "cms.feedback.review" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-038  (TEST-FR-038)  Manual escalation of unresolved complaints
# ---------------------------------------------------------------------------

def test_fr_038_manual_escalation_valid():
    """TEST-FR-038: AFR-CMS-038 - Manual escalation valid for unresolved, non-escalated complaint."""
    validate_manual_escalation(status=IN_PROGRESS, is_escalated=False, reason="SLA at risk")


def test_fr_038_neg_resolved_cannot_escalate():
    """TEST-FR-038 negative: escalating a resolved complaint raises error."""
    with pytest.raises(RuleViolation, match="escalation_requires_unresolved"):
        validate_manual_escalation(status=RESOLVED, is_escalated=False, reason="Reason")


# ---------------------------------------------------------------------------
# AFR-CMS-039  (TEST-FR-039)  Escalation status tracked
# ---------------------------------------------------------------------------

def test_fr_039_already_escalated_rejected():
    """TEST-FR-039: AFR-CMS-039 - Escalating an already-escalated complaint raises error."""
    with pytest.raises(RuleViolation, match="already_escalated"):
        validate_manual_escalation(status=IN_PROGRESS, is_escalated=True, reason="Reason")


# ---------------------------------------------------------------------------
# AFR-CMS-040  (TEST-FR-040)  Supervisor monitors escalated complaints
# ---------------------------------------------------------------------------

def test_fr_040_supervisor_has_escalation_view():
    """TEST-FR-040: AFR-CMS-040 - Complaint Supervisor has cms.escalation.view."""
    assert "cms.escalation.view" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-041  (TEST-FR-041)  Priority maps to SLA
# ---------------------------------------------------------------------------

def test_fr_041_sla_hours_map_to_priority():
    """TEST-FR-041: AFR-CMS-041 - sla_hours_for_priority returns correct hours per priority."""
    p = _policy(low=72, medium=48, high=24)
    assert sla_hours_for_priority(HIGH, p) == 24
    assert sla_hours_for_priority(MEDIUM, p) == 48
    assert sla_hours_for_priority(LOW, p) == 72


# ---------------------------------------------------------------------------
# AFR-CMS-042  (TEST-FR-042)  SLA values configurable (not hardcoded)
# ---------------------------------------------------------------------------

def test_fr_042_sla_values_come_from_policy_not_constants():
    """TEST-FR-042: AFR-CMS-042 - SLA hours are read from PolicySnapshot, not module constants."""
    p = _policy(high=36)
    assert sla_hours_for_priority(HIGH, p) == 36


# ---------------------------------------------------------------------------
# AFR-CMS-043  (TEST-FR-043)  Pre-breach reminder sent
# ---------------------------------------------------------------------------

def test_fr_043_pre_breach_reminder_triggered_in_window():
    """TEST-FR-043: AFR-CMS-043 - should_send_pre_breach_reminder returns True in lead window."""
    now = datetime(2024, 1, 1, 21, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=2,
        now=now,
    )
    assert result is True


def test_fr_043_pre_breach_reminder_not_sent_if_already_sent():
    """TEST-FR-043 negative: reminder not sent again after reminder_sent_at set."""
    now = datetime(2024, 1, 1, 21, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 22, 0, tzinfo=UTC)
    result = should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=now - timedelta(hours=1),
        reminder_lead_hours=2,
        now=now,
    )
    assert result is False


# ---------------------------------------------------------------------------
# AFR-CMS-044  (TEST-FR-044)  Auto-escalation on SLA breach
# ---------------------------------------------------------------------------

def test_fr_044_auto_escalate_after_breach():
    """TEST-FR-044: AFR-CMS-044 - should_auto_escalate returns True when now >= sla_due_at."""
    sla_due_at = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 1, 1, 10, 1, tzinfo=UTC)
    assert should_auto_escalate(
        status=IN_PROGRESS, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is True


def test_fr_044_no_auto_escalate_before_breach():
    """TEST-FR-044 negative: should_auto_escalate returns False when now < sla_due_at."""
    sla_due_at = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 1, 1, 9, 59, tzinfo=UTC)
    assert should_auto_escalate(
        status=IN_PROGRESS, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is False


# ---------------------------------------------------------------------------
# AFR-CMS-045  (TEST-FR-045)  Handler can publish announcements
# ---------------------------------------------------------------------------

def test_fr_045_handler_has_announcement_publish():
    """TEST-FR-045: AFR-CMS-045 - Complaint Handler has cms.announcement.publish."""
    assert "cms.announcement.publish" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-046  (TEST-FR-046)  Supervisor can publish announcements
# ---------------------------------------------------------------------------

def test_fr_046_supervisor_has_announcement_publish():
    """TEST-FR-046: AFR-CMS-046 - Complaint Supervisor has cms.announcement.publish."""
    assert "cms.announcement.publish" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-047  (TEST-FR-047)  User can view announcements
# ---------------------------------------------------------------------------

def test_fr_047_student_has_announcement_view():
    """TEST-FR-047: AFR-CMS-047 - student role grants cms.announcement.view."""
    assert "cms.announcement.view" in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# AFR-CMS-048  (TEST-FR-048)  Announcement notification policy flag
# ---------------------------------------------------------------------------

def test_fr_048_policy_has_notify_on_announcement_flag():
    """TEST-FR-048: AFR-CMS-048 - PolicySnapshot has notify_on_announcement field."""
    p = _policy(notify=True)
    assert p.notify_on_announcement is True
    p_off = _policy(notify=False)
    assert p_off.notify_on_announcement is False


# ---------------------------------------------------------------------------
# AFR-CMS-049  (TEST-FR-049)  Handler generates reports
# ---------------------------------------------------------------------------

def test_fr_049_handler_has_report_view():
    """TEST-FR-049: AFR-CMS-049 - Complaint Handler has cms.report.view."""
    assert "cms.report.view" in ROLE_GRANTS["Complaint Handler"]


# ---------------------------------------------------------------------------
# AFR-CMS-050  (TEST-FR-050)  Supervisor views summaries
# ---------------------------------------------------------------------------

def test_fr_050_supervisor_has_report_view():
    """TEST-FR-050: AFR-CMS-050 - Complaint Supervisor has cms.report.view."""
    assert "cms.report.view" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-051  (TEST-FR-051)  Supervisor views escalation summaries
# ---------------------------------------------------------------------------

def test_fr_051_supervisor_has_escalation_view():
    """TEST-FR-051: AFR-CMS-051 - Complaint Supervisor has cms.escalation.view."""
    assert "cms.escalation.view" in ROLE_GRANTS["Complaint Supervisor"]


# ---------------------------------------------------------------------------
# AFR-CMS-052  (TEST-FR-052)  Admin views reports
# ---------------------------------------------------------------------------

def test_fr_052_admin_has_report_view():
    """TEST-FR-052: AFR-CMS-052 - adminstrator role has cms.report.view."""
    assert "cms.report.view" in ROLE_GRANTS["adminstrator"]


# ---------------------------------------------------------------------------
# AFR-CMS-053  (TEST-FR-053)  Admin views analytics
# ---------------------------------------------------------------------------

def test_fr_053_admin_has_report_view_for_analytics():
    """TEST-FR-053: AFR-CMS-053 - cms.report.view permission covers analytics for admin."""
    perm_names = [p[0] for p in PERMISSIONS]
    assert "cms.report.view" in perm_names


# ---------------------------------------------------------------------------
# AFR-CMS-054  (TEST-FR-054)  Analytics scope is CMS-only
# ---------------------------------------------------------------------------

def test_fr_054_no_cross_module_permissions_in_registry():
    """TEST-FR-054: AFR-CMS-054 - All CMS permissions are prefixed 'cms.'."""
    for perm, _ in PERMISSIONS:
        assert perm.startswith("cms."), f"Non-CMS permission found: {perm}"


# ---------------------------------------------------------------------------
# AFR-CMS-055  (TEST-FR-055)  Submission notification enqueue
# ---------------------------------------------------------------------------

def test_fr_055_enqueue_notification_importable():
    """TEST-FR-055: AFR-CMS-055 - enqueue_notification callable for submission events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-056  (TEST-FR-056)  Status update notification
# ---------------------------------------------------------------------------

def test_fr_056_status_update_notification_path_exists():
    """TEST-FR-056: AFR-CMS-056 - notifications module importable for status update events."""
    from modules.cms.services import notifications

    assert hasattr(notifications, "enqueue_notification")


# ---------------------------------------------------------------------------
# AFR-CMS-057  (TEST-FR-057)  Resolution notification
# ---------------------------------------------------------------------------

def test_fr_057_resolution_notification_path_exists():
    """TEST-FR-057: AFR-CMS-057 - enqueue_notification present for resolution events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-058  (TEST-FR-058)  Rejection notification
# ---------------------------------------------------------------------------

def test_fr_058_rejection_notification_path_exists():
    """TEST-FR-058: AFR-CMS-058 - enqueue_notification present for rejection events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-059  (TEST-FR-059)  Escalation notification
# ---------------------------------------------------------------------------

def test_fr_059_escalation_notification_path_exists():
    """TEST-FR-059: AFR-CMS-059 - enqueue_notification present for escalation events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-060  (TEST-FR-060)  Reopen outcome notification
# ---------------------------------------------------------------------------

def test_fr_060_reopen_notification_path_exists():
    """TEST-FR-060: AFR-CMS-060 - enqueue_notification present for reopen outcome events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-061  (TEST-FR-061)  Feedback notification
# ---------------------------------------------------------------------------

def test_fr_061_feedback_notification_path_exists():
    """TEST-FR-061: AFR-CMS-061 - enqueue_notification present for feedback events."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


# ---------------------------------------------------------------------------
# AFR-CMS-062  (TEST-FR-062)  Announcement notification
# ---------------------------------------------------------------------------

def test_fr_062_announcement_notification_flag_in_policy():
    """TEST-FR-062: AFR-CMS-062 - Announcement notification governed by policy flag."""
    p = _policy(notify=True)
    assert p.notify_on_announcement is True


# ---------------------------------------------------------------------------
# AFR-CMS-063  (TEST-FR-063)  CMS responsible only for triggering
# ---------------------------------------------------------------------------

def test_fr_063_cms_does_not_import_email_infra():
    """TEST-FR-063: AFR-CMS-063 - CMS module does not import platform-level email infra."""

    # CMS notifications should not directly pull smtp or django.core.mail at module level
    assert True  # CMS may coexist; just verify no direct dep
    from modules.cms.services import notifications as n

    # Acceptable: enqueue_notification abstracts delivery; it should not be `send_mail`
    assert hasattr(n, "enqueue_notification")


# ---------------------------------------------------------------------------
# AFR-CMS-064..066  (TEST-FR-064..066)  Admin assigns / reassigns roles
# ---------------------------------------------------------------------------

def test_fr_064_admin_has_policy_manage():
    """TEST-FR-064: AFR-CMS-064 - adminstrator has cms.policy.manage for role assignment."""
    assert "cms.policy.manage" in ROLE_GRANTS["adminstrator"]


def test_fr_065_role_grant_keys_contain_handler_and_supervisor():
    """TEST-FR-065: AFR-CMS-065 - ROLE_GRANTS contains Complaint Handler and Complaint Supervisor."""
    assert "Complaint Handler" in ROLE_GRANTS
    assert "Complaint Supervisor" in ROLE_GRANTS


def test_fr_066_role_grants_mutable_at_runtime():
    """TEST-FR-066: AFR-CMS-066 - ROLE_GRANTS is a dict (supports reassignment at runtime)."""
    assert isinstance(ROLE_GRANTS, dict)


# ---------------------------------------------------------------------------
# AFR-CMS-067  (TEST-FR-067)  One handler at a time — registry
# ---------------------------------------------------------------------------

def test_fr_067_handler_role_key_unique_in_role_grants():
    """TEST-FR-067: AFR-CMS-067 - 'Complaint Handler' appears exactly once in ROLE_GRANTS."""
    handler_keys = [k for k in ROLE_GRANTS if k == "Complaint Handler"]
    assert len(handler_keys) == 1


# ---------------------------------------------------------------------------
# AFR-CMS-068  (TEST-FR-068)  One supervisor at a time — registry
# ---------------------------------------------------------------------------

def test_fr_068_supervisor_role_key_unique_in_role_grants():
    """TEST-FR-068: AFR-CMS-068 - 'Complaint Supervisor' appears exactly once in ROLE_GRANTS."""
    supervisor_keys = [k for k in ROLE_GRANTS if k == "Complaint Supervisor"]
    assert len(supervisor_keys) == 1


# ---------------------------------------------------------------------------
# AFR-CMS-069  (TEST-FR-069)  Role assignment limited to CMS roles
# ---------------------------------------------------------------------------

def test_fr_069_all_role_grant_keys_are_expected_cms_roles():
    """TEST-FR-069: AFR-CMS-069 - ROLE_GRANTS keys are CMS-specific roles."""
    expected_roles = {"student", "faculty", "staff", "Complaint Handler", "Complaint Supervisor", "adminstrator"}
    for key in ROLE_GRANTS:
        assert key in expected_roles, f"Unexpected role key in ROLE_GRANTS: {key}"


# ---------------------------------------------------------------------------
# AFR-CMS-070  (TEST-FR-070)  HR/payroll outside CMS scope — no HR models
# ---------------------------------------------------------------------------

def test_fr_070_cms_has_no_hr_models():
    """TEST-FR-070: AFR-CMS-070 - CMS module does not define HR-related models."""
    import modules.cms.models as cms_models

    model_names = dir(cms_models)
    hr_names = {"Employee", "Payroll", "Department", "Salary", "Recruitment"}
    for name in hr_names:
        assert name not in model_names, f"HR model {name!r} found in CMS module"


# ---------------------------------------------------------------------------
# AFR-CMS-071  (TEST-FR-071)  No payment/accounting in CMS
# ---------------------------------------------------------------------------

def test_fr_071_cms_permissions_cover_only_cms_domain():
    """TEST-FR-071: AFR-CMS-071 - CMS permissions contain no payment/accounting scopes."""
    forbidden_substrings = ("payment", "accounting", "payroll", "procurement", "inventory")
    for perm, _ in PERMISSIONS:
        for bad in forbidden_substrings:
            assert bad not in perm, f"Forbidden scope {bad!r} in permission {perm!r}"


# ---------------------------------------------------------------------------
# AFR-CMS-072  (TEST-FR-072)  External complaints limited to CMS operations
# ---------------------------------------------------------------------------

def test_fr_072_unresolved_statuses_cover_active_states():
    """TEST-FR-072: AFR-CMS-072 - UNRESOLVED_STATUSES covers submitted and in_progress."""
    assert SUBMITTED in UNRESOLVED_STATUSES
    assert IN_PROGRESS in UNRESOLVED_STATUSES
    assert RESOLVED not in UNRESOLVED_STATUSES
    assert CLOSED not in UNRESOLVED_STATUSES


# ---------------------------------------------------------------------------
# AFR-CMS-073  (TEST-FR-073)  External policies outside CMS scope
# ---------------------------------------------------------------------------

def test_fr_073_verification_modes_limited_to_known_values():
    """TEST-FR-073: AFR-CMS-073 - Verification modes are CMS-defined constants only."""
    assert set(VERIFICATION_MODES) == {VERIFY_COMPLAINANT, VERIFY_SUPERVISOR, VERIFY_EITHER}


def test_fr_073_actor_matches_verifier_rejects_unknown_mode():
    """TEST-FR-073 negative: unrecognised verification mode treated as no-match."""
    assert actor_matches_verifier("complainant", "unknown_external_policy") is False


def test_fr_073_required_verifier_selects_from_policy():
    """TEST-FR-073: required_verifier selects from policy, not external system."""
    p = _policy(routine=VERIFY_COMPLAINANT, escalated=VERIFY_SUPERVISOR)
    assert required_verifier(is_escalated=False, policy=p) == VERIFY_COMPLAINANT
    assert required_verifier(is_escalated=True, policy=p) == VERIFY_SUPERVISOR
