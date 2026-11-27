"""Specification tests for Business Rule (BR) strategy.

Generated from docs/19-cms/spec-tests/BR_DESIGN.json per Assignment 9 Prompt B.
Tests cover BR-CMS-001..041 (positive + negative for each active rule).
BR-CMS-042 is retired and skipped.
Tests that only use the domain layer run without a DB.
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
    validate_policy_values,
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
    ESCALATION_AUTOMATIC,
    ESCALATION_MANUAL,
    HANDLER,
    HIGH,
    IN_PROGRESS,
    LOW,
    MEDIUM,
    REJECTED,
    RESOLVED,
    STATUSES,
    SUBMITTED,
    SUPERVISOR,
    TERMINAL_STATUSES,
    UNRESOLVED_STATUSES,
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
# BR-CMS-001: Submissions open to all institutional users
# ---------------------------------------------------------------------------

def test_br_001_pos_validate_submission_passes():
    """TEST-BR-001: BR-CMS-001 positive - Valid submission accepted."""
    validate_submission("Title", "Description", category_active=True)


def test_br_002_neg_submission_inactive_category():
    """TEST-BR-002: BR-CMS-001 negative - Submission with inactive category rejected."""
    with pytest.raises(RuleViolation, match="category_inactive"):
        validate_submission("Title", "Desc", category_active=False)


# ---------------------------------------------------------------------------
# BR-CMS-002: Mandatory fields must be present
# ---------------------------------------------------------------------------

def test_br_003_pos_mandatory_fields_present():
    """TEST-BR-003: BR-CMS-002 positive - Both title and description provided."""
    validate_submission("Title", "Description", category_active=True)


def test_br_004_neg_blank_title_raises():
    """TEST-BR-004: BR-CMS-002 negative - Blank title raises RuleViolation."""
    with pytest.raises(RuleViolation, match="title_required"):
        validate_submission("  ", "Description", category_active=True)


# ---------------------------------------------------------------------------
# BR-CMS-003: Description mandatory
# ---------------------------------------------------------------------------

def test_br_005_pos_description_present():
    """TEST-BR-005: BR-CMS-003 positive - Description present and non-blank."""
    validate_submission("Title", "Some body", category_active=True)


def test_br_006_neg_blank_description_raises():
    """TEST-BR-006: BR-CMS-003 negative - Blank description raises RuleViolation."""
    with pytest.raises(RuleViolation, match="description_required"):
        validate_submission("Title", "", category_active=True)


# ---------------------------------------------------------------------------
# BR-CMS-004: Attachment count enforced
# ---------------------------------------------------------------------------

def test_br_007_pos_attachment_count_at_limit():
    """TEST-BR-007: BR-CMS-004 positive - Exactly max_attachments accepted."""
    validate_attachment_count(3, max_attachments=3)


def test_br_008_neg_attachment_count_exceeded():
    """TEST-BR-008: BR-CMS-004 negative - Exceeding limit raises RuleViolation."""
    with pytest.raises(RuleViolation, match="too_many_attachments"):
        validate_attachment_count(4, max_attachments=3)


# ---------------------------------------------------------------------------
# BR-CMS-005: Max attachments configurable via policy
# ---------------------------------------------------------------------------

def test_br_009_pos_policy_max_attachments_accepted():
    """TEST-BR-009: BR-CMS-005 positive - Policy-driven limit respected."""
    p = _policy(max_att=5)
    validate_attachment_count(5, max_attachments=p.max_attachments)


def test_br_010_neg_policy_max_attachments_violated():
    """TEST-BR-010: BR-CMS-005 negative - Violation of policy-driven limit rejected."""
    p = _policy(max_att=2)
    with pytest.raises(RuleViolation, match="too_many_attachments"):
        validate_attachment_count(3, max_attachments=p.max_attachments)


# ---------------------------------------------------------------------------
# BR-CMS-006: Complaint status recorded on each transition
# ---------------------------------------------------------------------------

def test_br_011_pos_all_statuses_in_tuple():
    """TEST-BR-011: BR-CMS-006 positive - All five statuses exist as constants."""
    assert set(STATUSES) == {"submitted", "in_progress", "resolved", "rejected", "closed"}


def test_br_012_neg_invalid_transition_raises():
    """TEST-BR-012: BR-CMS-006 negative - Invalid transition raises InvalidTransition."""
    from modules.cms.domain.state_machine import InvalidTransition

    with pytest.raises(InvalidTransition):
        check_transition(SUBMITTED, CLOSED, COMPLAINANT)


# ---------------------------------------------------------------------------
# BR-CMS-007: Handler must assign category for handling
# ---------------------------------------------------------------------------

def test_br_013_pos_handler_valid_category():
    """TEST-BR-013: BR-CMS-007 positive - Active category accepted in handling setup."""
    validate_handling_setup(HIGH, category_active=True, assigned_to_user_id=1, assigned_unit="")


def test_br_014_neg_handler_inactive_category():
    """TEST-BR-014: BR-CMS-007 negative - Inactive category in handling setup rejected."""
    with pytest.raises(RuleViolation, match="category_inactive"):
        validate_handling_setup(HIGH, category_active=False, assigned_to_user_id=1, assigned_unit="")


# ---------------------------------------------------------------------------
# BR-CMS-008: Handler must assign complaint
# ---------------------------------------------------------------------------

def test_br_015_pos_assignment_via_unit():
    """TEST-BR-015: BR-CMS-008 positive - Assignment via unit string accepted."""
    validate_handling_setup(HIGH, category_active=True, assigned_to_user_id=None, assigned_unit="IT Dept")


def test_br_016_neg_no_assignment_target():
    """TEST-BR-016: BR-CMS-008 negative - Neither user nor unit assigned raises error."""
    with pytest.raises(RuleViolation, match="assignment_target_required"):
        validate_handling_setup(HIGH, category_active=True, assigned_to_user_id=None, assigned_unit="   ")


# ---------------------------------------------------------------------------
# BR-CMS-009: Priority must be Low / Medium / High
# ---------------------------------------------------------------------------

def test_br_017_pos_all_valid_priorities_accepted():
    """TEST-BR-017: BR-CMS-009 positive - Low, Medium, High all pass."""
    for prio in (LOW, MEDIUM, HIGH):
        validate_handling_setup(prio, category_active=True, assigned_to_user_id=1, assigned_unit="")


def test_br_018_neg_invalid_priority_rejected():
    """TEST-BR-018: BR-CMS-009 negative - Unrecognised priority raises error."""
    with pytest.raises(RuleViolation, match="invalid_priority"):
        validate_handling_setup("Critical", category_active=True, assigned_to_user_id=1, assigned_unit="")


# ---------------------------------------------------------------------------
# BR-CMS-010: Assignment moves complaint to IN_PROGRESS
# ---------------------------------------------------------------------------

def test_br_019_pos_submitted_to_in_progress():
    """TEST-BR-019: BR-CMS-010 positive - SUBMITTED -> IN_PROGRESS transition allowed for handler."""
    t = check_transition(SUBMITTED, IN_PROGRESS, HANDLER, passed_guards={"has_handling_setup": True})
    assert t.to == IN_PROGRESS


def test_br_020_neg_non_handler_cannot_assign():
    """TEST-BR-020: BR-CMS-010 negative - Non-handler actor raises ActorNotAllowed."""
    from modules.cms.domain.state_machine import ActorNotAllowed

    with pytest.raises(ActorNotAllowed):
        check_transition(SUBMITTED, IN_PROGRESS, COMPLAINANT, passed_guards={"has_handling_setup": True})


# ---------------------------------------------------------------------------
# BR-CMS-011: Progress update stays IN_PROGRESS
# ---------------------------------------------------------------------------

def test_br_021_pos_in_progress_to_in_progress():
    """TEST-BR-021: BR-CMS-011 positive - IN_PROGRESS -> IN_PROGRESS transition valid."""
    t = check_transition(IN_PROGRESS, IN_PROGRESS, HANDLER, passed_guards={"has_progress_note": True})
    assert t.to == IN_PROGRESS


def test_br_022_neg_progress_note_guard_fails():
    """TEST-BR-022: BR-CMS-011 negative - Missing progress_note guard fails."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_progress_note"):
        check_transition(IN_PROGRESS, IN_PROGRESS, HANDLER, passed_guards={})


# ---------------------------------------------------------------------------
# BR-CMS-012: Lifecycle statuses defined
# ---------------------------------------------------------------------------

def test_br_023_pos_statuses_defined():
    """TEST-BR-023: BR-CMS-012 positive - All five statuses exist."""
    assert SUBMITTED == "submitted"
    assert IN_PROGRESS == "in_progress"
    assert RESOLVED == "resolved"
    assert REJECTED == "rejected"
    assert CLOSED == "closed"


def test_br_024_neg_rejected_is_terminal():
    """TEST-BR-024: BR-CMS-012 negative - REJECTED is a terminal status."""
    assert REJECTED in TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# BR-CMS-013: Resolution requires details
# ---------------------------------------------------------------------------

def test_br_025_pos_resolution_with_details():
    """TEST-BR-025: BR-CMS-013 positive - Resolution with details guard passes."""
    t = check_transition(IN_PROGRESS, RESOLVED, HANDLER, passed_guards={"has_resolution_details": True})
    assert t.to == RESOLVED


def test_br_026_neg_resolution_without_details():
    """TEST-BR-026: BR-CMS-013 negative - Resolution without details guard fails."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_resolution_details"):
        check_transition(IN_PROGRESS, RESOLVED, HANDLER, passed_guards={})


# ---------------------------------------------------------------------------
# BR-CMS-014: Rejection requires reason
# ---------------------------------------------------------------------------

def test_br_027_pos_rejection_with_reason():
    """TEST-BR-027: BR-CMS-014 positive - Rejection with reason guard passes."""
    t = check_transition(IN_PROGRESS, REJECTED, HANDLER, passed_guards={"has_rejection_reason": True})
    assert t.to == REJECTED


def test_br_028_neg_rejection_without_reason():
    """TEST-BR-028: BR-CMS-014 negative - Rejection without reason guard fails."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="has_rejection_reason"):
        check_transition(IN_PROGRESS, REJECTED, HANDLER, passed_guards={})


# ---------------------------------------------------------------------------
# BR-CMS-015: Complainant notified on outcome
# ---------------------------------------------------------------------------

def test_br_029_pos_notification_service_exists():
    """TEST-BR-029: BR-CMS-015 positive - enqueue_notification callable exists."""
    from modules.cms.services.notifications import enqueue_notification

    assert callable(enqueue_notification)


def test_br_030_neg_resolved_still_needs_verifier_to_close():
    """TEST-BR-030: BR-CMS-015 negative - RESOLVED cannot jump to CLOSED without verifier guard."""
    from modules.cms.domain.state_machine import GuardFailed

    with pytest.raises(GuardFailed, match="matches_required_verifier"):
        check_transition(RESOLVED, CLOSED, COMPLAINANT, passed_guards={})


# ---------------------------------------------------------------------------
# BR-CMS-016: Verification mode configurable per policy
# ---------------------------------------------------------------------------

def test_br_031_pos_verification_mode_complainant():
    """TEST-BR-031: BR-CMS-016 positive - Complainant actor matches VERIFY_COMPLAINANT mode."""
    assert actor_matches_verifier(COMPLAINANT, VERIFY_COMPLAINANT) is True


def test_br_032_neg_handler_does_not_match_verifier():
    """TEST-BR-032: BR-CMS-016 negative - Handler cannot verify (mode=complainant)."""
    assert actor_matches_verifier(HANDLER, VERIFY_COMPLAINANT) is False


# ---------------------------------------------------------------------------
# BR-CMS-017: Either complainant or supervisor can verify
# ---------------------------------------------------------------------------

def test_br_033_pos_either_mode_accepts_both():
    """TEST-BR-033: BR-CMS-017 positive - VERIFY_EITHER accepts complainant and supervisor."""
    assert actor_matches_verifier(COMPLAINANT, VERIFY_EITHER) is True
    assert actor_matches_verifier(SUPERVISOR, VERIFY_EITHER) is True


def test_br_034_neg_either_mode_rejects_handler():
    """TEST-BR-034: BR-CMS-017 negative - VERIFY_EITHER rejects handler."""
    assert actor_matches_verifier(HANDLER, VERIFY_EITHER) is False


# ---------------------------------------------------------------------------
# BR-CMS-018: Reopen only allowed on closed complaints
# ---------------------------------------------------------------------------

def test_br_035_pos_reopen_on_closed():
    """TEST-BR-035: BR-CMS-018 positive - Reopen request valid when status is closed."""
    validate_reopen_request(status=CLOSED, reason="Dissatisfied", has_pending=False)


def test_br_036_neg_reopen_on_non_closed():
    """TEST-BR-036: BR-CMS-018 negative - Reopen on non-closed status raises error."""
    with pytest.raises(RuleViolation, match="reopen_requires_closed"):
        validate_reopen_request(status=RESOLVED, reason="Reason", has_pending=False)


# ---------------------------------------------------------------------------
# BR-CMS-019: Reopen reason mandatory
# ---------------------------------------------------------------------------

def test_br_037_pos_reopen_with_reason():
    """TEST-BR-037: BR-CMS-019 positive - Reopen request with reason accepted."""
    validate_reopen_request(status=CLOSED, reason="Issue persists", has_pending=False)


def test_br_038_neg_reopen_without_reason():
    """TEST-BR-038: BR-CMS-019 negative - Reopen request without reason raises error."""
    with pytest.raises(RuleViolation, match="reopen_reason_required"):
        validate_reopen_request(status=CLOSED, reason="   ", has_pending=False)


# ---------------------------------------------------------------------------
# BR-CMS-020: Only one pending reopen request at a time
# ---------------------------------------------------------------------------

def test_br_039_pos_no_existing_pending_reopen():
    """TEST-BR-039: BR-CMS-020 positive - Request succeeds when no pending request exists."""
    validate_reopen_request(status=CLOSED, reason="Issue persists", has_pending=False)


def test_br_040_neg_duplicate_reopen_rejected():
    """TEST-BR-040: BR-CMS-020 negative - Duplicate reopen request raises error."""
    with pytest.raises(RuleViolation, match="reopen_already_pending"):
        validate_reopen_request(status=CLOSED, reason="Issue persists", has_pending=True)


# ---------------------------------------------------------------------------
# BR-CMS-021: Supervisor decides on reopen requests
# ---------------------------------------------------------------------------

def test_br_041_pos_supervisor_can_reopen():
    """TEST-BR-041: BR-CMS-021 positive - Supervisor can approve reopen."""
    t = check_transition(CLOSED, IN_PROGRESS, SUPERVISOR, passed_guards={"has_pending_reopen_request": True})
    assert t is not None


def test_br_042_neg_handler_cannot_reopen():
    """TEST-BR-042: BR-CMS-021 negative - Handler cannot approve reopen (ActorNotAllowed)."""
    from modules.cms.domain.state_machine import ActorNotAllowed

    with pytest.raises(ActorNotAllowed):
        check_transition(CLOSED, IN_PROGRESS, HANDLER, passed_guards={"has_pending_reopen_request": True})


# ---------------------------------------------------------------------------
# BR-CMS-022: Feedback only after resolution or closure
# ---------------------------------------------------------------------------

def test_br_043_pos_feedback_after_resolved():
    """TEST-BR-043: BR-CMS-022 positive - Feedback on resolved complaint accepted."""
    validate_feedback(status=RESOLVED, rating=5, already_submitted=False)


def test_br_044_neg_feedback_on_in_progress():
    """TEST-BR-044: BR-CMS-022 negative - Feedback on in-progress complaint rejected."""
    with pytest.raises(RuleViolation, match="feedback_not_allowed"):
        validate_feedback(status=IN_PROGRESS, rating=5, already_submitted=False)


# ---------------------------------------------------------------------------
# BR-CMS-023: Feedback rating must be 1-5
# ---------------------------------------------------------------------------

def test_br_045_pos_valid_rating():
    """TEST-BR-045: BR-CMS-023 positive - Rating of 3 accepted."""
    validate_feedback(status=RESOLVED, rating=3, already_submitted=False)


def test_br_046_neg_invalid_rating_zero():
    """TEST-BR-046: BR-CMS-023 negative - Rating of 0 raises RuleViolation."""
    with pytest.raises(RuleViolation, match="invalid_rating"):
        validate_feedback(status=RESOLVED, rating=0, already_submitted=False)


def test_br_046b_neg_invalid_rating_six():
    """TEST-BR-046b: BR-CMS-023 negative - Rating of 6 raises RuleViolation."""
    with pytest.raises(RuleViolation, match="invalid_rating"):
        validate_feedback(status=RESOLVED, rating=6, already_submitted=False)


# ---------------------------------------------------------------------------
# BR-CMS-024: Manual escalation requires unresolved and unesclated status
# ---------------------------------------------------------------------------

def test_br_047_pos_manual_escalation_in_progress():
    """TEST-BR-047: BR-CMS-024 positive - Unresolved, non-escalated complaint can be escalated."""
    validate_manual_escalation(status=IN_PROGRESS, is_escalated=False, reason="Approaching SLA")


def test_br_048_neg_manual_escalation_resolved():
    """TEST-BR-048: BR-CMS-024 negative - Resolved complaint cannot be escalated."""
    with pytest.raises(RuleViolation, match="escalation_requires_unresolved"):
        validate_manual_escalation(status=RESOLVED, is_escalated=False, reason="Reason")


# ---------------------------------------------------------------------------
# BR-CMS-025: Escalation types
# ---------------------------------------------------------------------------

def test_br_049_pos_escalation_type_constants():
    """TEST-BR-049: BR-CMS-025 positive - Escalation type constants defined correctly."""
    assert ESCALATION_MANUAL == "manual"
    assert ESCALATION_AUTOMATIC == "automatic"


def test_br_050_neg_already_escalated():
    """TEST-BR-050: BR-CMS-025 negative - Already-escalated complaint raises error on re-escalate."""
    with pytest.raises(RuleViolation, match="already_escalated"):
        validate_manual_escalation(status=IN_PROGRESS, is_escalated=True, reason="Reason")


# ---------------------------------------------------------------------------
# BR-CMS-026: SLA hours by priority
# ---------------------------------------------------------------------------

def test_br_051_pos_sla_hours_high():
    """TEST-BR-051: BR-CMS-026 positive - High priority maps to 24h SLA."""
    p = _policy(high=24)
    assert sla_hours_for_priority(HIGH, p) == 24


def test_br_052_neg_invalid_priority_sla():
    """TEST-BR-052: BR-CMS-026 negative - Unknown priority string raises RuleViolation."""
    p = _policy()
    with pytest.raises(RuleViolation, match="invalid_priority"):
        sla_hours_for_priority("Critical", p)


# ---------------------------------------------------------------------------
# BR-CMS-027: SLA values configurable
# ---------------------------------------------------------------------------

def test_br_053_pos_sla_values_read_from_policy():
    """TEST-BR-053: BR-CMS-027 positive - SLA hours sourced from PolicySnapshot."""
    p = _policy(low=96, medium=72, high=48)
    assert sla_hours_for_priority(LOW, p) == 96
    assert sla_hours_for_priority(MEDIUM, p) == 72
    assert sla_hours_for_priority(HIGH, p) == 48


def test_br_054_neg_policy_values_must_be_positive():
    """TEST-BR-054: BR-CMS-027 negative - Non-positive SLA hours rejected by validate_policy_values."""
    with pytest.raises(RuleViolation, match="invalid_sla_hours"):
        validate_policy_values(
            low_sla_hours=0,
            medium_sla_hours=48,
            high_sla_hours=24,
            reminder_lead_hours=4,
            max_attachments=3,
            routine_verification_by=VERIFY_COMPLAINANT,
            escalated_verification_by=VERIFY_SUPERVISOR,
        )


# ---------------------------------------------------------------------------
# BR-CMS-028: Pre-breach reminder sent once
# ---------------------------------------------------------------------------

def test_br_055_pos_reminder_in_window():
    """TEST-BR-055: BR-CMS-028 positive - Reminder triggered inside lead window."""
    now = datetime(2024, 1, 1, 21, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 22, 0, tzinfo=UTC)
    assert should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=2,
        now=now,
    ) is True


def test_br_056_neg_reminder_already_sent():
    """TEST-BR-056: BR-CMS-028 negative - Reminder suppressed if already sent."""
    now = datetime(2024, 1, 1, 21, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 22, 0, tzinfo=UTC)
    assert should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=now - timedelta(hours=1),
        reminder_lead_hours=2,
        now=now,
    ) is False


# ---------------------------------------------------------------------------
# BR-CMS-029: Auto-escalation on SLA breach
# ---------------------------------------------------------------------------

def test_br_057_pos_auto_escalate_at_breach():
    """TEST-BR-057: BR-CMS-029 positive - Auto-escalation triggered at breach time."""
    sla_due_at = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    assert should_auto_escalate(
        status=IN_PROGRESS, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is True


def test_br_058_neg_no_auto_escalate_resolved():
    """TEST-BR-058: BR-CMS-029 negative - Auto-escalation skipped for resolved status."""
    sla_due_at = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    now = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
    assert should_auto_escalate(
        status=RESOLVED, is_escalated=False, sla_due_at=sla_due_at, now=now
    ) is False


# ---------------------------------------------------------------------------
# BR-CMS-030: Reminder lead configurable
# ---------------------------------------------------------------------------

def test_br_059_pos_custom_reminder_lead_hours():
    """TEST-BR-059: BR-CMS-030 positive - Custom 6h lead triggers reminder correctly."""
    now = datetime(2024, 1, 1, 18, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 24, 0, tzinfo=UTC)
    assert should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=6,
        now=now,
    ) is True


def test_br_060_neg_reminder_lead_before_window():
    """TEST-BR-060: BR-CMS-030 negative - Reminder not sent before lead window begins."""
    now = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    sla_due_at = datetime(2024, 1, 1, 24, 0, tzinfo=UTC)
    assert should_send_pre_breach_reminder(
        status=IN_PROGRESS,
        is_escalated=False,
        sla_due_at=sla_due_at,
        reminder_sent_at=None,
        reminder_lead_hours=2,
        now=now,
    ) is False


# ---------------------------------------------------------------------------
# BR-CMS-031: Handler can publish announcements
# ---------------------------------------------------------------------------

def test_br_061_pos_handler_can_publish():
    """TEST-BR-061: BR-CMS-031 positive - Handler has cms.announcement.publish."""
    assert "cms.announcement.publish" in ROLE_GRANTS["Complaint Handler"]


def test_br_062_neg_student_cannot_publish():
    """TEST-BR-062: BR-CMS-031 negative - student role lacks cms.announcement.publish."""
    assert "cms.announcement.publish" not in ROLE_GRANTS["student"]


# ---------------------------------------------------------------------------
# BR-CMS-032: Supervisor can publish announcements
# ---------------------------------------------------------------------------

def test_br_063_pos_supervisor_can_publish():
    """TEST-BR-063: BR-CMS-032 positive - Supervisor has cms.announcement.publish."""
    assert "cms.announcement.publish" in ROLE_GRANTS["Complaint Supervisor"]


def test_br_064_neg_admin_cannot_publish_announcements():
    """TEST-BR-064: BR-CMS-032 negative - adminstrator lacks cms.announcement.publish."""
    assert "cms.announcement.publish" not in ROLE_GRANTS["adminstrator"]


# ---------------------------------------------------------------------------
# BR-CMS-033: Announcement notification governed by policy
# ---------------------------------------------------------------------------

def test_br_065_pos_policy_notify_on_announcement_true():
    """TEST-BR-065: BR-CMS-033 positive - notify_on_announcement can be True."""
    p = _policy(notify=True)
    assert p.notify_on_announcement is True


def test_br_066_neg_policy_notify_on_announcement_false():
    """TEST-BR-066: BR-CMS-033 negative - notify_on_announcement can be False (no notification)."""
    p = _policy(notify=False)
    assert p.notify_on_announcement is False


# ---------------------------------------------------------------------------
# BR-CMS-034: Verification mode must be from known set
# ---------------------------------------------------------------------------

def test_br_067_pos_all_verification_modes_valid():
    """TEST-BR-067: BR-CMS-034 positive - Three valid verification modes defined."""
    assert set(VERIFICATION_MODES) == {VERIFY_COMPLAINANT, VERIFY_SUPERVISOR, VERIFY_EITHER}


def test_br_068_neg_unknown_verification_mode_in_policy():
    """TEST-BR-068: BR-CMS-034 negative - Unknown verification mode rejected by validate_policy_values."""
    with pytest.raises(RuleViolation, match="invalid_verification_mode"):
        validate_policy_values(
            low_sla_hours=72,
            medium_sla_hours=48,
            high_sla_hours=24,
            reminder_lead_hours=4,
            max_attachments=3,
            routine_verification_by="auto",
            escalated_verification_by=VERIFY_SUPERVISOR,
        )


# ---------------------------------------------------------------------------
# BR-CMS-035: Reminder lead must be < shortest SLA
# ---------------------------------------------------------------------------

def test_br_069_pos_reminder_lead_valid():
    """TEST-BR-069: BR-CMS-035 positive - reminder_lead_hours < min SLA accepted."""
    validate_policy_values(
        low_sla_hours=72,
        medium_sla_hours=48,
        high_sla_hours=24,
        reminder_lead_hours=4,
        max_attachments=3,
        routine_verification_by=VERIFY_COMPLAINANT,
        escalated_verification_by=VERIFY_SUPERVISOR,
    )


def test_br_070_neg_reminder_lead_exceeds_min_sla():
    """TEST-BR-070: BR-CMS-035 negative - reminder_lead >= min SLA rejected."""
    with pytest.raises(RuleViolation, match="invalid_reminder_lead"):
        validate_policy_values(
            low_sla_hours=72,
            medium_sla_hours=48,
            high_sla_hours=24,
            reminder_lead_hours=24,
            max_attachments=3,
            routine_verification_by=VERIFY_COMPLAINANT,
            escalated_verification_by=VERIFY_SUPERVISOR,
        )


# ---------------------------------------------------------------------------
# BR-CMS-036: Max attachments between 0 and 20
# ---------------------------------------------------------------------------

def test_br_071_pos_max_attachments_at_boundary():
    """TEST-BR-071: BR-CMS-036 positive - max_attachments of 0 and 20 accepted."""
    for att in (0, 20):
        validate_policy_values(
            low_sla_hours=72,
            medium_sla_hours=48,
            high_sla_hours=24,
            reminder_lead_hours=4,
            max_attachments=att,
            routine_verification_by=VERIFY_COMPLAINANT,
            escalated_verification_by=VERIFY_SUPERVISOR,
        )


def test_br_072_neg_max_attachments_above_20():
    """TEST-BR-072: BR-CMS-036 negative - max_attachments of 21 raises error."""
    with pytest.raises(RuleViolation, match="invalid_max_attachments"):
        validate_policy_values(
            low_sla_hours=72,
            medium_sla_hours=48,
            high_sla_hours=24,
            reminder_lead_hours=4,
            max_attachments=21,
            routine_verification_by=VERIFY_COMPLAINANT,
            escalated_verification_by=VERIFY_SUPERVISOR,
        )


# ---------------------------------------------------------------------------
# BR-CMS-037: Unresolved statuses defined
# ---------------------------------------------------------------------------

def test_br_073_pos_unresolved_statuses_set():
    """TEST-BR-073: BR-CMS-037 positive - UNRESOLVED_STATUSES contains submitted and in_progress."""
    assert SUBMITTED in UNRESOLVED_STATUSES
    assert IN_PROGRESS in UNRESOLVED_STATUSES


def test_br_074_neg_resolved_not_unresolved():
    """TEST-BR-074: BR-CMS-037 negative - RESOLVED not in UNRESOLVED_STATUSES."""
    assert RESOLVED not in UNRESOLVED_STATUSES


# ---------------------------------------------------------------------------
# BR-CMS-038: Feedback not duplicated
# ---------------------------------------------------------------------------

def test_br_075_pos_first_feedback_accepted():
    """TEST-BR-075: BR-CMS-038 positive - First feedback submission passes."""
    validate_feedback(status=RESOLVED, rating=4, already_submitted=False)


def test_br_076_neg_duplicate_feedback_rejected():
    """TEST-BR-076: BR-CMS-038 negative - Second feedback submission raises error."""
    with pytest.raises(RuleViolation, match="feedback_already_submitted"):
        validate_feedback(status=RESOLVED, rating=4, already_submitted=True)


# ---------------------------------------------------------------------------
# BR-CMS-039: Escalation reason required
# ---------------------------------------------------------------------------

def test_br_077_pos_escalation_with_reason():
    """TEST-BR-077: BR-CMS-039 positive - Escalation with reason accepted."""
    validate_manual_escalation(status=IN_PROGRESS, is_escalated=False, reason="Approaching breach")


def test_br_078_neg_escalation_without_reason():
    """TEST-BR-078: BR-CMS-039 negative - Escalation without reason raises error."""
    with pytest.raises(RuleViolation, match="escalation_reason_required"):
        validate_manual_escalation(status=IN_PROGRESS, is_escalated=False, reason="  ")


# ---------------------------------------------------------------------------
# BR-CMS-040: required_verifier selects from policy
# ---------------------------------------------------------------------------

def test_br_079_pos_required_verifier_routine():
    """TEST-BR-079: BR-CMS-040 positive - required_verifier returns routine mode for non-escalated."""
    p = _policy(routine=VERIFY_COMPLAINANT, escalated=VERIFY_SUPERVISOR)
    assert required_verifier(is_escalated=False, policy=p) == VERIFY_COMPLAINANT


def test_br_080_neg_required_verifier_escalated():
    """TEST-BR-080: BR-CMS-040 negative - Escalated complaint uses escalated verification mode."""
    p = _policy(routine=VERIFY_COMPLAINANT, escalated=VERIFY_SUPERVISOR)
    assert required_verifier(is_escalated=True, policy=p) == VERIFY_SUPERVISOR


# ---------------------------------------------------------------------------
# BR-CMS-041: SLA due_at computed from base time + hours
# ---------------------------------------------------------------------------

def test_br_081_pos_sla_due_at_calculation():
    """TEST-BR-081: BR-CMS-041 positive - SLA due_at = base_time + SLA hours."""
    base = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
    p = _policy(high=24)
    due = compute_sla_due_at(base, HIGH, p)
    assert due == base + timedelta(hours=24)


def test_br_082_neg_sla_due_at_different_priorities():
    """TEST-BR-082: BR-CMS-041 negative - LOW priority has longer SLA than HIGH."""
    base = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
    p = _policy(low=72, high=24)
    due_high = compute_sla_due_at(base, HIGH, p)
    due_low = compute_sla_due_at(base, LOW, p)
    assert due_low > due_high


# ---------------------------------------------------------------------------
# BR-CMS-042: RETIRED — skipped
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="NOT_AUTOMATED: BR-CMS-042 is retired per specification.")
def test_br_083_br_042_retired():
    """TEST-BR-083: BR-CMS-042 - Retired rule; skipped per spec."""
