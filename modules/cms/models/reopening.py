from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.cms.models.complaint import Complaint


class ReopenRequest(TimeStampedModel):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (DENIED, "Denied"),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="reopen_requests"
    )
    requested_by_user_id = models.IntegerField(db_index=True)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["complaint"],
                condition=Q(status="pending"),
                name="cms_reopen_single_pending_uniq",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "approved", "denied"]),
                name="cms_reopen_status_valid_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "-created_at"], name="cms_reopen_status_created_idx"
            ),
        ]
