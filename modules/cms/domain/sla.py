from __future__ import annotations

from datetime import datetime, timedelta

from modules.cms.domain.rules import PolicySnapshot, RuleViolation
from modules.cms.domain.state_machine import HIGH, LOW, MEDIUM, UNRESOLVED_STATUSES


def sla_hours_for_priority(priority: str, policy: PolicySnapshot) -> int:
    # BR-CMS-026, BR-CMS-027, AFR-CMS-041, AFR-CMS-042: map priority to active policy SLA hours.
    mapping = {
        LOW: policy.low_sla_hours,
        MEDIUM: policy.medium_sla_hours,
        HIGH: policy.high_sla_hours,
    }
    if priority not in mapping:
        raise RuleViolation("invalid_priority", "Priority must be Low, Medium, or High.")
    return mapping[priority]


def compute_sla_due_at(base_time: datetime, priority: str, policy: PolicySnapshot) -> datetime:
    return base_time + timedelta(hours=sla_hours_for_priority(priority, policy))


def should_send_pre_breach_reminder(
    *,
    status: str,
    is_escalated: bool,
    sla_due_at: datetime | None,
    reminder_sent_at: datetime | None,
    reminder_lead_hours: int,
    now: datetime,
) -> bool:
    # BR-CMS-028, AFR-CMS-043, UC-CMS-021: approaching breach, unresolved, not reminded.
    if (
        status not in UNRESOLVED_STATUSES
        or is_escalated
        or sla_due_at is None
        or reminder_sent_at is not None
    ):
        return False
    reminder_at = sla_due_at - timedelta(hours=reminder_lead_hours)
    return reminder_at <= now < sla_due_at


def should_auto_escalate(
    *,
    status: str,
    is_escalated: bool,
    sla_due_at: datetime | None,
    now: datetime,
) -> bool:
    # BR-CMS-029, AFR-CMS-044, UC-CMS-022, BW-CMS-08: unresolved complaint past SLA due time.
    if status not in UNRESOLVED_STATUSES or is_escalated or sla_due_at is None:
        return False
    return now >= sla_due_at
