from __future__ import annotations

import logging
import uuid

from django.db import transaction

from core.api.exceptions import DomainError, NotFoundError
from core.files import drive
from core.files.validators import sanitise_filename
from modules.cms.domain.rules import (
    RuleViolation,
    validate_attachment_count,
    validate_submission,
)
from modules.cms.domain.state_machine import SUBMITTED
from modules.cms.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintHistory,
)
from modules.cms.services.notifications import enqueue_notification
from modules.cms.services.policy import require_active_policy

logger = logging.getLogger(__name__)


def _next_tracking_code() -> str:
    return f"CMS-{uuid.uuid4().hex[:8].upper()}"


def submit_complaint(
    *,
    actor,
    category_id: int,
    title: str,
    description: str,
    attachments: list[dict] | None = None,
) -> Complaint:
    # UC-CMS-001, CFR-CMS-001, AFR-CMS-001..010, BR-CMS-001..006.
    policy = require_active_policy()
    category = ComplaintCategory.objects.filter(pk=category_id).first()
    if category is None:
        raise NotFoundError(
            "Selected complaint category was not found.", code="category_not_found"
        )

    items = attachments or []
    try:
        validate_submission(
            title=title, description=description, category_active=category.is_active
        )
        validate_attachment_count(len(items), policy.max_attachments)
    except RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    parsed_attachments: list[tuple[str, drive.DriveRef]] = []
    for raw in items:
        try:
            ref = drive.parse(raw.get("url", ""))
        except drive.InvalidDriveLink as exc:
            raise DomainError(exc.message, code=exc.code) from exc
        label = sanitise_filename(raw.get("label") or "attachment", fallback="attachment")
        parsed_attachments.append((label, ref))

    with transaction.atomic():
        complaint = Complaint.objects.create(
            tracking_code=_next_tracking_code(),
            user_id=actor.user_id,
            category=category,
            policy=policy,
            title=title.strip(),
            description=description.strip(),
            status=SUBMITTED,
        )
        for label, ref in parsed_attachments:
            ComplaintAttachment.objects.create(
                complaint=complaint,
                uploaded_by_user_id=actor.user_id,
                label=label,
                drive_file_id=ref.file_id,
                url=ref.url,
            )
        ComplaintHistory.objects.create(
            complaint=complaint,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or actor.kind,
            event_type="submitted",
            from_status="",
            to_status=SUBMITTED,
            note="Complaint submitted.",
        )
        enqueue_notification(
            event_type="complaint_submitted",
            subject=f"Complaint {complaint.tracking_code} submitted",
            message=f"Your complaint {complaint.tracking_code} has been registered.",
            dedupe_key=f"cms:submitted:{complaint.id}",
            recipient_user_id=actor.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.submitted complaint_id=%d actor_id=%d", complaint.id, actor.user_id
    )
    return complaint
