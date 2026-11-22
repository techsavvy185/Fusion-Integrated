from __future__ import annotations

from dataclasses import dataclass

from modules.cms.domain.state_machine import (
    CLOSED,
    COMPLAINANT,
    RESOLVED,
    SUPERVISOR,
    UNRESOLVED_STATUSES,
    VALID_PRIORITIES,
)

# BR-CMS-016, ISS-CMS-010: policy verification modes.
VERIFY_COMPLAINANT = "complainant"
VERIFY_SUPERVISOR = "supervisor"
VERIFY_EITHER = "either"
VERIFICATION_MODES = (VERIFY_COMPLAINANT, VERIFY_SUPERVISOR, VERIFY_EITHER)


class RuleViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PolicySnapshot:
    low_sla_hours: int
    medium_sla_hours: int
    high_sla_hours: int
    reminder_lead_hours: int
    max_attachments: int
    routine_verification_by: str
    escalated_verification_by: str
    notify_on_announcement: bool


def validate_submission(title: str, description: str, category_active: bool) -> None:
    # BR-CMS-002, AFR-CMS-006: mandatory fields must be present and non-blank.
    if not (title or "").strip():
        raise RuleViolation(
            "title_required", "Provide a short title describing your complaint."
        )
    if not (description or "").strip():
        raise RuleViolation(
            "description_required", "Provide a description of the complaint before submitting."
        )
    if not category_active:
        raise RuleViolation("category_inactive", "Select an active complaint category.")


def validate_attachment_count(count: int, max_attachments: int) -> None:
    # BR-CMS-004, BR-CMS-005, AFR-CMS-007, AFR-CMS-008: configurable attachment limit.
    if count > max_attachments:
        raise RuleViolation(
            "too_many_attachments",
            f"At most {max_attachments} supporting attachments are allowed per complaint.",
        )


def validate_priority(priority: str) -> str:
    # BR-CMS-009, AFR-CMS-013: priority restricted to Low, Medium, High.
    if priority not in VALID_PRIORITIES:
        raise RuleViolation("invalid_priority", "Priority must be Low, Medium, or High.")
    return priority


def validate_handling_setup(
    priority: str, category_active: bool, assigned_to_user_id: int | None, assigned_unit: str
) -> None:
    # BR-CMS-007, BR-CMS-008, BR-CMS-009, BR-CMS-010, ISS-CMS-009: manual assignment validation.
    if not category_active:
        raise RuleViolation("category_inactive", "Select an active complaint category.")
    validate_priority(priority)
    if assigned_to_user_id is None and not (assigned_unit or "").strip():
        raise RuleViolation(
            "assignment_target_required",
            "Assign the complaint to a person or an operational unit.",
        )


def required_verifier(is_escalated: bool, policy: PolicySnapshot) -> str:
    # BR-CMS-016, AFR-CMS-027, AFR-CMS-028, ISS-CMS-010: select verifier from policy.
    return policy.escalated_verification_by if is_escalated else policy.routine_verification_by


def actor_matches_verifier(actor_kind: str, mode: str) -> bool:
    if mode == VERIFY_EITHER:
        return actor_kind in (COMPLAINANT, SUPERVISOR)
    if mode == VERIFY_COMPLAINANT:
        return actor_kind == COMPLAINANT
    if mode == VERIFY_SUPERVISOR:
        return actor_kind == SUPERVISOR
    return False


def validate_reopen_request(status: str, reason: str, has_pending: bool) -> None:
    # BR-CMS-018, AFR-CMS-030, UC-CMS-008: only closed complaints with a reason.
    if status != CLOSED:
        raise RuleViolation(
            "reopen_requires_closed", "Only a closed complaint can be requested for reopening."
        )
    if has_pending:
        raise RuleViolation(
            "reopen_already_pending",
            "A reopening request is already pending for this complaint.",
        )
    if not (reason or "").strip():
        raise RuleViolation(
            "reopen_reason_required", "Explain why the complaint should be reopened."
        )


def validate_feedback(status: str, rating: int, already_submitted: bool) -> None:
    # BR-CMS-022, AFR-CMS-035, UC-CMS-009: feedback only after resolution or closure.
    if status not in (RESOLVED, CLOSED):
        raise RuleViolation(
            "feedback_not_allowed",
            "Feedback can only be submitted after the complaint is resolved or closed.",
        )
    if already_submitted:
        raise RuleViolation(
            "feedback_already_submitted",
            "Feedback has already been submitted for this complaint.",
        )
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise RuleViolation("invalid_rating", "Rating must be a whole number from 1 to 5.")


def validate_manual_escalation(status: str, is_escalated: bool, reason: str) -> None:
    # BR-CMS-024, AFR-CMS-038, UC-CMS-011, BW-CMS-07: escalate unresolved non-escalated complaint.
    if status not in UNRESOLVED_STATUSES:
        raise RuleViolation(
            "escalation_requires_unresolved", "Only unresolved complaints can be escalated."
        )
    if is_escalated:
        raise RuleViolation("already_escalated", "This complaint is already escalated.")
    if not (reason or "").strip():
        raise RuleViolation(
            "escalation_reason_required", "Provide a reason for escalating this complaint."
        )


def validate_policy_values(
    low_sla_hours: int,
    medium_sla_hours: int,
    high_sla_hours: int,
    reminder_lead_hours: int,
    max_attachments: int,
    routine_verification_by: str,
    escalated_verification_by: str,
) -> None:
    # BR-CMS-005, BR-CMS-027: policy invariants.
    if any(
        v <= 0 for v in (low_sla_hours, medium_sla_hours, high_sla_hours, reminder_lead_hours)
    ):
        raise RuleViolation(
            "invalid_sla_hours",
            "SLA durations and reminder lead hours must be positive numbers.",
        )
    if reminder_lead_hours >= min(low_sla_hours, medium_sla_hours, high_sla_hours):
        raise RuleViolation(
            "invalid_reminder_lead",
            "Reminder lead hours must be shorter than the shortest SLA duration.",
        )
    if max_attachments < 0 or max_attachments > 20:
        raise RuleViolation(
            "invalid_max_attachments",
            "Maximum attachments per complaint must be between 0 and 20.",
        )
    if (
        routine_verification_by not in VERIFICATION_MODES
        or escalated_verification_by not in VERIFICATION_MODES
    ):
        raise RuleViolation(
            "invalid_verification_mode",
            "Verification mode must be complainant, supervisor, or either.",
        )
