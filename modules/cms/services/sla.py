from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from modules.cms.domain.sla import should_auto_escalate, should_send_pre_breach_reminder
from modules.cms.domain.state_machine import ESCALATION_AUTOMATIC, SYSTEM, UNRESOLVED_STATUSES
from modules.cms.models import Complaint, ComplaintHistory
from modules.cms.services.notifications import enqueue_notification

logger = logging.getLogger(__name__)


def send_pre_breach_reminders(*, now=None) -> int:
    # UC-CMS-021, CFR-CMS-009, AFR-CMS-043, BR-CMS-028: idempotent pre-breach reminder sweep.
    current = now or timezone.now()
    reminded = 0
    candidate_ids = list(
        Complaint.objects.filter(
            status__in=UNRESOLVED_STATUSES,
            is_escalated=False,
            sla_due_at__isnull=False,
            reminder_sent_at__isnull=True,
        ).values_list("id", flat=True)
    )
    for cid in candidate_ids:
        with transaction.atomic():
            complaint = (
                Complaint.objects.select_for_update()
                .select_related("policy")
                .filter(pk=cid)
                .first()
            )
            if complaint is None:
                continue
            if not should_send_pre_breach_reminder(
                status=complaint.status,
                is_escalated=complaint.is_escalated,
                sla_due_at=complaint.sla_due_at,
                reminder_sent_at=complaint.reminder_sent_at,
                reminder_lead_hours=complaint.policy.reminder_lead_hours,
                now=current,
            ):
                continue
            complaint.reminder_sent_at = current
            complaint.save(update_fields=["reminder_sent_at", "updated_at"])
            enqueue_notification(
                event_type="sla_pre_breach_reminder",
                subject=f"SLA reminder for {complaint.tracking_code}",
                message=f"Complaint {complaint.tracking_code} is approaching its SLA deadline.",
                dedupe_key=f"cms:sla_reminder:{complaint.id}:{complaint.reopen_count}",
                recipient_user_id=complaint.assigned_to_user_id,
                complaint=complaint,
            )
            reminded += 1
    if reminded:
        logger.info("cms.sla.reminders_sent count=%d", reminded)
    return reminded


def escalate_breached_complaints(*, now=None) -> int:
    # UC-CMS-022, CFR-CMS-009, AFR-CMS-044, BR-CMS-029, BW-CMS-08, CW-CMS-03.
    current = now or timezone.now()
    escalated = 0
    candidate_ids = list(
        Complaint.objects.filter(
            status__in=UNRESOLVED_STATUSES,
            is_escalated=False,
            sla_due_at__isnull=False,
            sla_due_at__lte=current,
        ).values_list("id", flat=True)
    )
    for cid in candidate_ids:
        with transaction.atomic():
            complaint = Complaint.objects.select_for_update().filter(pk=cid).first()
            if complaint is None:
                continue
            if not should_auto_escalate(
                status=complaint.status,
                is_escalated=complaint.is_escalated,
                sla_due_at=complaint.sla_due_at,
                now=current,
            ):
                continue
            complaint.is_escalated = True
            complaint.escalation_type = ESCALATION_AUTOMATIC
            complaint.escalated_at = current
            complaint.escalation_reason = "Automatically escalated due to SLA breach."
            complaint.save(
                update_fields=[
                    "is_escalated",
                    "escalation_type",
                    "escalated_at",
                    "escalation_reason",
                    "updated_at",
                ]
            )
            ComplaintHistory.objects.create(
                complaint=complaint,
                actor_user_id=None,
                actor_role=SYSTEM,
                event_type="escalated_automatic",
                from_status=complaint.status,
                to_status=complaint.status,
                note="Automatically escalated due to SLA breach.",
            )
            enqueue_notification(
                event_type="complaint_escalated",
                subject=f"Complaint {complaint.tracking_code} escalated (SLA breach)",
                message=f"Complaint {complaint.tracking_code} breached SLA and escalated.",
                dedupe_key=f"cms:escalated:{complaint.id}",
                recipient_user_id=complaint.user_id,
                complaint=complaint,
            )
            escalated += 1
    if escalated:
        logger.info("cms.sla.auto_escalated count=%d", escalated)
    return escalated
