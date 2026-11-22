from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.cms.domain.rules import RuleViolation, validate_manual_escalation
from modules.cms.domain.state_machine import ESCALATION_MANUAL
from modules.cms.models import Complaint, ComplaintHistory
from modules.cms.services.notifications import enqueue_notification

logger = logging.getLogger(__name__)


def escalate_manually(*, actor, complaint_id: int, reason: str) -> Complaint:
    # UC-CMS-011, CFR-CMS-008, AFR-CMS-038, AFR-CMS-039, BR-CMS-024, BR-CMS-025, BW-CMS-07.
    clean_reason = (reason or "").strip()
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        if complaint.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot escalate your own complaint.", code="self_action_forbidden"
            )
        try:
            validate_manual_escalation(complaint.status, complaint.is_escalated, clean_reason)
        except RuleViolation as exc:
            if exc.code in ("escalation_requires_unresolved", "already_escalated"):
                raise ConflictError(exc.message, code=exc.code) from exc
            raise DomainError(exc.message, code=exc.code) from exc

        complaint.is_escalated = True
        complaint.escalation_type = ESCALATION_MANUAL
        complaint.escalated_at = timezone.now()
        complaint.escalation_reason = clean_reason
        complaint.save()

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "Complaint Handler",
            event_type="escalated_manual",
            from_status=complaint.status,
            to_status=complaint.status,
            note=clean_reason,
        )
        enqueue_notification(
            event_type="complaint_escalated",
            subject=f"Complaint {complaint.tracking_code} escalated",
            message=f"Complaint {complaint.tracking_code} was escalated for review.",
            dedupe_key=f"cms:escalated:{complaint.id}",
            recipient_user_id=complaint.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.escalated_manual complaint_id=%d actor_id=%d",
        complaint.id,
        actor.user_id,
    )
    return complaint
