from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.cms.models.complaint import Complaint


class ComplaintFeedback(TimeStampedModel):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="feedback_entries"
    )
    submitted_by_user_id = models.IntegerField(db_index=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["complaint"], name="cms_feedback_one_per_complaint_uniq"
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5), name="cms_feedback_rating_range_chk"
            ),
        ]
        indexes = [
            models.Index(fields=["-created_at"], name="cms_feedback_created_idx"),
        ]
