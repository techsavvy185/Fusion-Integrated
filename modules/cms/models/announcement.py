from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class ComplaintAnnouncement(TimeStampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_by_user_id = models.IntegerField(db_index=True)
    published_by_role = models.CharField(max_length=64)
    published_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        indexes = [
            models.Index(
                fields=["is_active", "-published_at"], name="cms_announce_active_pub_idx"
            ),
        ]
