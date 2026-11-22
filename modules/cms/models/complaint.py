from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.cms.domain.state_machine import (
    CLOSED,
    ESCALATION_AUTOMATIC,
    ESCALATION_MANUAL,
    HIGH,
    IN_PROGRESS,
    LOW,
    MEDIUM,
    REJECTED,
    RESOLVED,
    SUBMITTED,
)
from modules.cms.models.policy import CmsPolicy, ComplaintCategory


class Complaint(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (SUBMITTED, "Submitted"),
        (IN_PROGRESS, "In Progress"),
        (RESOLVED, "Resolved"),
        (REJECTED, "Rejected"),
        (CLOSED, "Closed"),
    ]
    PRIORITY_CHOICES = [
        ("", "Unassigned"),
        (LOW, "Low"),
        (MEDIUM, "Medium"),
        (HIGH, "High"),
    ]
    ESCALATION_CHOICES = [
        ("", "None"),
        (ESCALATION_MANUAL, "Manual"),
        (ESCALATION_AUTOMATIC, "Automatic"),
    ]

    tracking_code = models.CharField(max_length=32)
    category = models.ForeignKey(
        ComplaintCategory, on_delete=models.PROTECT, related_name="complaints"
    )
    policy = models.ForeignKey(CmsPolicy, on_delete=models.PROTECT, related_name="complaints")
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SUBMITTED)
    priority = models.CharField(
        max_length=16, choices=PRIORITY_CHOICES, blank=True, default=""
    )
    assigned_to_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_unit = models.CharField(max_length=120, blank=True, default="")
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    is_escalated = models.BooleanField(default=False)
    escalation_type = models.CharField(
        max_length=16, choices=ESCALATION_CHOICES, blank=True, default=""
    )
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True, default="")
    resolution_details = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by_user_id = models.IntegerField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_by_role = models.CharField(max_length=32, blank=True, default="")
    reopen_count = models.PositiveIntegerField(default=0)
    last_reopened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tracking_code"], name="cms_complaint_tracking_code_uniq"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[SUBMITTED, IN_PROGRESS, RESOLVED, REJECTED, CLOSED]),
                name="cms_complaint_status_valid_chk",
            ),
            models.CheckConstraint(
                condition=Q(priority__in=["", LOW, MEDIUM, HIGH]),
                name="cms_complaint_priority_valid_chk",
            ),
            models.CheckConstraint(
                condition=Q(escalation_type__in=["", ESCALATION_MANUAL, ESCALATION_AUTOMATIC]),
                name="cms_complaint_esc_type_valid_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"], name="cms_complaint_user_created_idx"
            ),
            models.Index(fields=["status", "-created_at"], name="cms_complaint_status_cr_idx"),
            models.Index(
                fields=["is_escalated", "status", "-created_at"],
                name="cms_complaint_esc_status_idx",
            ),
            models.Index(
                fields=["sla_due_at", "status", "is_escalated"],
                name="cms_complaint_sla_sweep_idx",
            ),
        ]

    @property
    def has_handling_setup(self) -> bool:
        return bool(
            self.priority and (self.assigned_to_user_id is not None or self.assigned_unit)
        )


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="attachments"
    )
    uploaded_by_user_id = models.IntegerField()
    label = models.CharField(max_length=120)
    drive_file_id = models.CharField(max_length=200)
    url = models.URLField(max_length=500)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["complaint", "created_at"], name="cms_attach_complaint_idx"),
        ]


class ComplaintHistory(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64)
    event_type = models.CharField(max_length=40)
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20, blank=True, default="")
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["complaint", "created_at"], name="cms_history_complaint_idx"),
        ]
