from datetime import UTC, datetime, timedelta

import pytest

from modules.cms.domain.rules import (
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
    validate_priority,
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
    HANDLER,
    HIGH,
    IN_PROGRESS,
    LOW,
    MEDIUM,
    RESOLVED,
    SUBMITTED,
    SUPERVISOR,
)


def _policy():
    return PolicySnapshot(
        low_sla_hours=72,
        medium_sla_hours=48,
        high_sla_hours=24,
        reminder_lead_hours=4,
        max_attachments=3,
        routine_verification_by=VERIFY_COMPLAINANT,
        escalated_verification_by=VERIFY_SUPERVISOR,
        notify_on_announcement=True,
    )


def test_validate_submission_rules():
    # BR-CMS-002, AFR-CMS-006: valid and invalid submission inputs.
    validate_submission("Wi-Fi down", "No signal in room 101", True)
    with pytest.raises(RuleViolation) as exc1:
        validate_submission("   ", "desc", True)
    assert exc1.value.code == "title_required"
    with pytest.raises(RuleViolation) as exc2:
        validate_submission("title", "   ", True)
    assert exc2.value.code == "description_required"
    with pytest.raises(RuleViolation) as exc3:
        validate_submission("title", "desc", False)
    assert exc3.value.code == "category_inactive"


def test_validate_attachments_and_priority_and_setup():
    # BR-CMS-004, BR-CMS-005, BR-CMS-007..010, AFR-CMS-007, AFR-CMS-008, AFR-CMS-013.
    validate_attachment_count(3, 3)
    with pytest.raises(RuleViolation) as exc:
        validate_attachment_count(4, 3)
    assert exc.value.code == "too_many_attachments"

    assert validate_priority(LOW) == LOW
    assert validate_priority(MEDIUM) == MEDIUM
    assert validate_priority(HIGH) == HIGH
    with pytest.raises(RuleViolation) as excp:
        validate_priority("Urgent")
    assert excp.value.code == "invalid_priority"

    validate_handling_setup(HIGH, True, 202, "")
    validate_handling_setup(LOW, True, None, "Electrical Section")
    with pytest.raises(RuleViolation) as exc_cat:
        validate_handling_setup(LOW, False, 202, "")
    assert exc_cat.value.code == "category_inactive"
    with pytest.raises(RuleViolation) as exc_tgt:
        validate_handling_setup(LOW, True, None, "   ")
    assert exc_tgt.value.code == "assignment_target_required"


def test_verifier_selection_and_matching():
    # BR-CMS-016, AFR-CMS-027, AFR-CMS-028, ISS-CMS-010.
    p = _policy()
    assert required_verifier(False, p) == VERIFY_COMPLAINANT
    assert required_verifier(True, p) == VERIFY_SUPERVISOR
    assert actor_matches_verifier(COMPLAINANT, VERIFY_COMPLAINANT) is True
    assert actor_matches_verifier(SUPERVISOR, VERIFY_COMPLAINANT) is False
    assert actor_matches_verifier(SUPERVISOR, VERIFY_SUPERVISOR) is True
    assert actor_matches_verifier(COMPLAINANT, VERIFY_SUPERVISOR) is False
    assert actor_matches_verifier(COMPLAINANT, VERIFY_EITHER) is True
    assert actor_matches_verifier(SUPERVISOR, VERIFY_EITHER) is True
    assert actor_matches_verifier(HANDLER, VERIFY_EITHER) is False
    assert actor_matches_verifier(COMPLAINANT, "unknown") is False


def test_reopen_feedback_escalation_and_policy_validation():
    # BR-CMS-018, BR-CMS-022, BR-CMS-024, BR-CMS-027.
    validate_reopen_request(CLOSED, "Still leaking", False)
    with pytest.raises(RuleViolation) as e1:
        validate_reopen_request(RESOLVED, "Still leaking", False)
    assert e1.value.code == "reopen_requires_closed"
    with pytest.raises(RuleViolation) as e2:
        validate_reopen_request(CLOSED, "Still leaking", True)
    assert e2.value.code == "reopen_already_pending"
    with pytest.raises(RuleViolation) as e3:
        validate_reopen_request(CLOSED, "   ", False)
    assert e3.value.code == "reopen_reason_required"

    validate_feedback(RESOLVED, 5, False)
    validate_feedback(CLOSED, 1, False)
    with pytest.raises(RuleViolation) as f1:
        validate_feedback(IN_PROGRESS, 5, False)
    assert f1.value.code == "feedback_not_allowed"
    with pytest.raises(RuleViolation) as f2:
        validate_feedback(RESOLVED, 5, True)
    assert f2.value.code == "feedback_already_submitted"
    with pytest.raises(RuleViolation) as f3:
        validate_feedback(RESOLVED, 0, False)
    assert f3.value.code == "invalid_rating"
    with pytest.raises(RuleViolation) as f4:
        validate_feedback(RESOLVED, 6, False)
    assert f4.value.code == "invalid_rating"

    validate_manual_escalation(SUBMITTED, False, "Needs urgent attention")
    validate_manual_escalation(IN_PROGRESS, False, "Stuck with vendor")
    with pytest.raises(RuleViolation) as m1:
        validate_manual_escalation(CLOSED, False, "reason")
    assert m1.value.code == "escalation_requires_unresolved"
    with pytest.raises(RuleViolation) as m2:
        validate_manual_escalation(IN_PROGRESS, True, "reason")
    assert m2.value.code == "already_escalated"
    with pytest.raises(RuleViolation) as m3:
        validate_manual_escalation(IN_PROGRESS, False, " ")
    assert m3.value.code == "escalation_reason_required"

    validate_policy_values(72, 48, 24, 4, 5, VERIFY_COMPLAINANT, VERIFY_SUPERVISOR)
    with pytest.raises(RuleViolation) as p1:
        validate_policy_values(0, 48, 24, 4, 5, VERIFY_COMPLAINANT, VERIFY_SUPERVISOR)
    assert p1.value.code == "invalid_sla_hours"
    with pytest.raises(RuleViolation) as p2:
        validate_policy_values(72, 48, 24, 24, 5, VERIFY_COMPLAINANT, VERIFY_SUPERVISOR)
    assert p2.value.code == "invalid_reminder_lead"
    with pytest.raises(RuleViolation) as p3:
        validate_policy_values(72, 48, 24, 4, 25, VERIFY_COMPLAINANT, VERIFY_SUPERVISOR)
    assert p3.value.code == "invalid_max_attachments"
    with pytest.raises(RuleViolation) as p4:
        validate_policy_values(72, 48, 24, 4, 5, "bad", VERIFY_SUPERVISOR)
    assert p4.value.code == "invalid_verification_mode"


def test_sla_calculations_reminders_and_breaches():
    # BR-CMS-026, BR-CMS-027, BR-CMS-028, BR-CMS-029, AFR-CMS-041..044.
    p = _policy()
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    assert sla_hours_for_priority(LOW, p) == 72
    assert sla_hours_for_priority(MEDIUM, p) == 48
    assert sla_hours_for_priority(HIGH, p) == 24
    with pytest.raises(RuleViolation):
        sla_hours_for_priority("Critical", p)

    due = compute_sla_due_at(now, HIGH, p)
    assert due == now + timedelta(hours=24)

    # Too early for reminder.
    assert (
        should_send_pre_breach_reminder(
            status=IN_PROGRESS,
            is_escalated=False,
            sla_due_at=due,
            reminder_sent_at=None,
            reminder_lead_hours=4,
            now=now + timedelta(hours=19),
        )
        is False
    )
    # Inside reminder window.
    assert (
        should_send_pre_breach_reminder(
            status=IN_PROGRESS,
            is_escalated=False,
            sla_due_at=due,
            reminder_sent_at=None,
            reminder_lead_hours=4,
            now=now + timedelta(hours=21),
        )
        is True
    )
    # Already reminded or resolved or escalated or breached.
    assert (
        should_send_pre_breach_reminder(
            status=IN_PROGRESS,
            is_escalated=False,
            sla_due_at=due,
            reminder_sent_at=now,
            reminder_lead_hours=4,
            now=now + timedelta(hours=21),
        )
        is False
    )
    assert (
        should_send_pre_breach_reminder(
            status=RESOLVED,
            is_escalated=False,
            sla_due_at=due,
            reminder_sent_at=None,
            reminder_lead_hours=4,
            now=now + timedelta(hours=21),
        )
        is False
    )
    assert (
        should_send_pre_breach_reminder(
            status=IN_PROGRESS,
            is_escalated=False,
            sla_due_at=due,
            reminder_sent_at=None,
            reminder_lead_hours=4,
            now=due,
        )
        is False
    )

    # Auto-escalation checks.
    assert (
        should_auto_escalate(
            status=SUBMITTED,
            is_escalated=False,
            sla_due_at=due,
            now=due - timedelta(minutes=1),
        )
        is False
    )
    assert (
        should_auto_escalate(status=SUBMITTED, is_escalated=False, sla_due_at=due, now=due)
        is True
    )
    assert (
        should_auto_escalate(
            status=RESOLVED, is_escalated=False, sla_due_at=due, now=due + timedelta(hours=1)
        )
        is False
    )
    assert (
        should_auto_escalate(
            status=IN_PROGRESS, is_escalated=True, sla_due_at=due, now=due + timedelta(hours=1)
        )
        is False
    )
    assert (
        should_auto_escalate(
            status=IN_PROGRESS,
            is_escalated=False,
            sla_due_at=None,
            now=due + timedelta(hours=1),
        )
        is False
    )
