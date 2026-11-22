from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.cms.models import ComplaintAnnouncement
from modules.cms.services.notifications import enqueue_notification
from modules.cms.services.policy import require_active_policy

logger = logging.getLogger(__name__)


def publish_announcement(*, actor, title: str, body: str) -> ComplaintAnnouncement:
    # UC-CMS-013, CFR-CMS-010, AFR-CMS-045..048, AFR-CMS-062, BR-CMS-030, BR-CMS-031.
    clean_title = (title or "").strip()
    clean_body = (body or "").strip()
    if not clean_title or not clean_body:
        raise DomainError(
            "Provide both a title and body for the announcement.", code="announcement_invalid"
        )

    policy = require_active_policy()
    with transaction.atomic():
        ann = ComplaintAnnouncement.objects.create(
            title=clean_title,
            body=clean_body,
            published_by_user_id=actor.user_id,
            published_by_role=actor.active_role or actor.kind,
            published_at=timezone.now(),
            is_active=True,
        )
        if policy.notify_on_announcement:
            enqueue_notification(
                event_type="announcement_published",
                subject=f"CMS Announcement: {ann.title}",
                message=ann.body,
                dedupe_key=f"cms:announcement:{ann.id}",
                recipient_user_id=None,
                announcement=ann,
            )
    logger.info(
        "cms.announcement.published announcement_id=%d actor_id=%d", ann.id, actor.user_id
    )
    return ann
