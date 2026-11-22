from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.cms.models import CmsNotificationEvent, Complaint, ComplaintAnnouncement

logger = logging.getLogger(__name__)


def enqueue_notification(
    *,
    event_type: str,
    subject: str,
    message: str,
    dedupe_key: str,
    recipient_user_id: int | None = None,
    complaint: Complaint | None = None,
    announcement: ComplaintAnnouncement | None = None,
) -> CmsNotificationEvent | None:
    # BR-CMS-015, BR-CMS-034, CFR-CMS-012, AFR-CMS-055..063: outbox notification trigger.
    try:
        with transaction.atomic():
            event, _ = CmsNotificationEvent.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    "complaint": complaint,
                    "announcement": announcement,
                    "recipient_user_id": recipient_user_id,
                    "event_type": event_type,
                    "subject": subject[:200],
                    "message": message,
                },
            )
            return event
    except IntegrityError:
        return CmsNotificationEvent.objects.filter(dedupe_key=dedupe_key).first()


def dispatch_pending_notifications(*, limit: int = 100) -> int:
    # ADR-0006, BR-CMS-034: idempotent outbox drain (marks queued events dispatched).
    now = timezone.now()
    dispatched = 0
    with transaction.atomic():
        pending = list(
            CmsNotificationEvent.objects.select_for_update(skip_locked=True)
            .filter(dispatched_at__isnull=True)
            .order_by("created_at", "id")[:limit]
        )
        for event in pending:
            event.dispatched_at = now
            event.save(update_fields=["dispatched_at", "updated_at"])
            dispatched += 1
    if dispatched:
        logger.info("cms.notifications.dispatched count=%d", dispatched)
    return dispatched
