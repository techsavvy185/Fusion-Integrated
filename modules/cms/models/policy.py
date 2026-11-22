from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.cms.domain.rules import (
    VERIFY_COMPLAINANT,
    VERIFY_EITHER,
    VERIFY_SUPERVISOR,
    PolicySnapshot,
)


class ComplaintCategory(TimeStampedModel):
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="cms_category_code_uniq"),
        ]
        indexes = [
            models.Index(fields=["is_active", "name"], name="cms_category_active_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


class CmsPolicy(TimeStampedModel):
    VERIFICATION_CHOICES = [
        (VERIFY_COMPLAINANT, "Complainant"),
        (VERIFY_SUPERVISOR, "Supervisor"),
        (VERIFY_EITHER, "Either"),
    ]

    version = models.PositiveIntegerField()
    effective_from = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    low_sla_hours = models.PositiveIntegerField()
    medium_sla_hours = models.PositiveIntegerField()
    high_sla_hours = models.PositiveIntegerField()
    reminder_lead_hours = models.PositiveIntegerField()
    max_attachments = models.PositiveSmallIntegerField(default=5)
    routine_verification_by = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default=VERIFY_COMPLAINANT
    )
    escalated_verification_by = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default=VERIFY_SUPERVISOR
    )
    notify_on_announcement = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["version"], name="cms_policy_version_uniq"),
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="cms_policy_single_active_uniq",
            ),
            models.CheckConstraint(
                condition=Q(
                    low_sla_hours__gt=0,
                    medium_sla_hours__gt=0,
                    high_sla_hours__gt=0,
                    reminder_lead_hours__gt=0,
                ),
                name="cms_policy_positive_hours_chk",
            ),
            models.CheckConstraint(
                condition=Q(reminder_lead_hours__lt=F("high_sla_hours")),
                name="cms_policy_reminder_lt_high_sla_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "-effective_from"], name="cms_policy_active_eff_idx"
            ),
        ]

    def to_snapshot(self) -> PolicySnapshot:
        return PolicySnapshot(
            low_sla_hours=self.low_sla_hours,
            medium_sla_hours=self.medium_sla_hours,
            high_sla_hours=self.high_sla_hours,
            reminder_lead_hours=self.reminder_lead_hours,
            max_attachments=self.max_attachments,
            routine_verification_by=self.routine_verification_by,
            escalated_verification_by=self.escalated_verification_by,
            notify_on_announcement=self.notify_on_announcement,
        )
