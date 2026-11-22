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
from modules.cms.domain.rules import RuleViolation, validate_handling_setup
from modules.cms.domain.sla import compute_sla_due_at
from modules.cms.domain.state_machine import HANDLER, UNRESOLVED_STATUSES
from modules.cms.models import Complaint, ComplaintCategory, ComplaintHistory
from modules.cms.services.notifications import enqueue_notification
from modules.cms.services.transitions import transition_to_in_progress_locked

logger = logging.getLogger(__name__)


def setup_complaint_handling(
    *,
    actor,
    complaint_id: int,
    category_id: int | None,
    priority: str,
    assigned_to_user_id: int | None = None,
    assigned_unit: str = "",
) -> Complaint:
    # UC-CMS-004, CFR-CMS-002, AFR-CMS-011..015, BR-CMS-007..010, BR-CMS-026, ISS-CMS-009.
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("category", "policy")
            .filter(pk=complaint_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        if complaint.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot assign or prioritize your own complaint.",
                code="self_action_forbidden",
            )
        if complaint.status not in UNRESOLVED_STATUSES:
            raise ConflictError(
                "Handling setup can only be updated while a complaint is unresolved.",
                code="invalid_state",
            )

        category = complaint.category
        if category_id is not None and category_id != complaint.category_id:
            category = ComplaintCategory.objects.filter(pk=category_id).first()
            if category is None:
                raise NotFoundError(
                    "Selected complaint category was not found.", code="category_not_found"
                )

        try:
            validate_handling_setup(
                priority=priority,
                category_active=category.is_active,
                assigned_to_user_id=assigned_to_user_id,
                assigned_unit=assigned_unit,
            )
        except RuleViolation as exc:
            raise DomainError(exc.message, code=exc.code) from exc

        now = timezone.now()
        complaint.category = category
        complaint.priority = priority
        complaint.assigned_to_user_id = assigned_to_user_id
        complaint.assigned_unit = (assigned_unit or "").strip()
        complaint.assigned_by_user_id = actor.user_id
        complaint.assigned_at = now
        complaint.sla_due_at = compute_sla_due_at(
            now, priority, complaint.policy.to_snapshot()
        )
        complaint.reminder_sent_at = None
        complaint.save()

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "Complaint Handler",
            event_type="handling_setup",
            from_status=complaint.status,
            to_status=complaint.status,
            note=f"{category.code}/{priority}/{complaint.assigned_unit or 'user'}",
        )
    logger.info(
        "cms.complaint.handling_setup complaint_id=%d actor_id=%d", complaint.id, actor.user_id
    )
    return complaint


def record_progress_update(*, actor, complaint_id: int, note: str) -> Complaint:
    # UC-CMS-005, CFR-CMS-003, AFR-CMS-019..021, BR-CMS-011, BR-CMS-015, ISS-CMS-007.
    clean_note = (note or "").strip()
    if not clean_note:
        raise DomainError(
            "Provide a progress note before updating the complaint.",
            code="progress_note_required",
        )

    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("policy")
            .filter(pk=complaint_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        if complaint.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot update progress on your own complaint.",
                code="self_action_forbidden",
            )

        transition_to_in_progress_locked(
            complaint=complaint,
            actor_kind=HANDLER,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "Complaint Handler",
            passed_guards={
                "has_handling_setup": complaint.has_handling_setup,
                "has_progress_note": bool(clean_note),
            },
            event_type="progress_updated",
            note=clean_note,
        )
        history_count = complaint.history.count()
        enqueue_notification(
            event_type="complaint_status_updated",
            subject=f"Update on complaint {complaint.tracking_code}",
            message=f"Progress updated on complaint {complaint.tracking_code}.",
            dedupe_key=f"cms:progress:{complaint.id}:{history_count}",
            recipient_user_id=complaint.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.progress_updated complaint_id=%d actor_id=%d",
        complaint.id,
        actor.user_id,
    )
    return complaint
