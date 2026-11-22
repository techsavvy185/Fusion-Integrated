from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.cms.models.announcement import ComplaintAnnouncement
from modules.cms.models.complaint import Complaint


class CmsNotificationEvent(TimeStampedModel):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_events",
    )
    announcement = models.ForeignKey(
        ComplaintAnnouncement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_events",
    )
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=48)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    dedupe_key = models.CharField(max_length=120, unique=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["dispatched_at", "created_at"], name="cms_notif_dispatch_idx"
            ),
        ]
