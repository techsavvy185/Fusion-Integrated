from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.cms.domain.rules import RuleViolation, validate_policy_values
from modules.cms.models import CmsPolicy, ComplaintCategory


def require_active_policy() -> CmsPolicy:
    # BR-CMS-027, Step 2.8: never 500 when policy is unseeded.
    policy = CmsPolicy.objects.filter(is_active=True).order_by("-version").first()
    if policy is None:
        raise DomainError(
            "CMS policy is not configured. Run manage.py seed_cms_policy.",
            code="cms_policy_not_configured",
        )
    return policy


def create_category(*, code: str, name: str, description: str = "") -> ComplaintCategory:
    # BR-CMS-008: create active complaint category.
    clean_code = (code or "").strip().upper()
    clean_name = (name or "").strip()
    if not clean_code or not clean_name:
        raise DomainError(
            "Provide both a category code and a category name.", code="category_invalid"
        )
    try:
        with transaction.atomic():
            return ComplaintCategory.objects.create(
                code=clean_code,
                name=clean_name,
                description=(description or "").strip(),
                is_active=True,
            )
    except IntegrityError as exc:
        raise ConflictError(
            f"Category code {clean_code!r} already exists.", code="category_duplicate"
        ) from exc


def publish_policy(
    *,
    actor_user_id: int,
    low_sla_hours: int,
    medium_sla_hours: int,
    high_sla_hours: int,
    reminder_lead_hours: int,
    max_attachments: int,
    routine_verification_by: str,
    escalated_verification_by: str,
    notify_on_announcement: bool,
) -> CmsPolicy:
    # BR-CMS-005, BR-CMS-027, BR-CMS-031: effective-dated versioned policy.
    try:
        validate_policy_values(
            low_sla_hours=low_sla_hours,
            medium_sla_hours=medium_sla_hours,
            high_sla_hours=high_sla_hours,
            reminder_lead_hours=reminder_lead_hours,
            max_attachments=max_attachments,
            routine_verification_by=routine_verification_by,
            escalated_verification_by=escalated_verification_by,
        )
    except RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    with transaction.atomic():
        latest = CmsPolicy.objects.select_for_update().order_by("-version").first()
        next_version = (latest.version + 1) if latest else 1
        CmsPolicy.objects.filter(is_active=True).update(is_active=False)
        return CmsPolicy.objects.create(
            version=next_version,
            effective_from=timezone.now(),
            is_active=True,
            low_sla_hours=low_sla_hours,
            medium_sla_hours=medium_sla_hours,
            high_sla_hours=high_sla_hours,
            reminder_lead_hours=reminder_lead_hours,
            max_attachments=max_attachments,
            routine_verification_by=routine_verification_by,
            escalated_verification_by=escalated_verification_by,
            notify_on_announcement=notify_on_announcement,
            created_by_user_id=actor_user_id,
        )
