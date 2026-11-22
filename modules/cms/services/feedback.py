from __future__ import annotations

import logging

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.cms.domain.rules import RuleViolation, validate_feedback
from modules.cms.models import Complaint, ComplaintFeedback, ComplaintHistory
from modules.cms.services.notifications import enqueue_notification

logger = logging.getLogger(__name__)


def submit_feedback(
    *, actor, complaint_id: int, rating: int, comment: str = ""
) -> ComplaintFeedback:
    # UC-CMS-009, CFR-CMS-007, AFR-CMS-035, AFR-CMS-061, BR-CMS-022.
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None or complaint.user_id != actor.user_id:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        already = ComplaintFeedback.objects.filter(complaint=complaint).exists()
        try:
            validate_feedback(complaint.status, rating, already)
        except RuleViolation as exc:
            if exc.code in ("feedback_not_allowed", "feedback_already_submitted"):
                raise ConflictError(exc.message, code=exc.code) from exc
            raise DomainError(exc.message, code=exc.code) from exc
        try:
            fb = ComplaintFeedback.objects.create(
                complaint=complaint,
                submitted_by_user_id=actor.user_id,
                rating=rating,
                comment=(comment or "").strip(),
            )
        except IntegrityError as exc:
            raise ConflictError(
                "Feedback has already been submitted for this complaint.",
                code="feedback_already_submitted",
            ) from exc

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or actor.kind,
            event_type="feedback_submitted",
            from_status=complaint.status,
            to_status=complaint.status,
            note=f"Rating {rating}/5",
        )
        enqueue_notification(
            event_type="complaint_feedback_submitted",
            subject=f"Feedback received on {complaint.tracking_code}",
            message=f"Complainant submitted feedback ({rating}/5) for {complaint.tracking_code}.",
            dedupe_key=f"cms:feedback:{fb.id}",
            recipient_user_id=complaint.assigned_to_user_id,
            complaint=complaint,
        )
    logger.info("cms.feedback.submitted complaint_id=%d feedback_id=%d", complaint.id, fb.id)
    return fb
