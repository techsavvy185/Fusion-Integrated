from __future__ import annotations

from django.db.models import QuerySet

from modules.cms.models import (
    CmsPolicy,
    Complaint,
    ComplaintAnnouncement,
    ComplaintCategory,
    ComplaintFeedback,
    ReopenRequest,
)


def _is_handler(actor) -> bool:
    return bool(actor and actor.has_permission("cms.complaint.update"))


def _is_supervisor(actor) -> bool:
    return bool(actor and actor.has_permission("cms.escalation.view"))


def _is_admin(actor) -> bool:
    return bool(actor and actor.has_permission("cms.policy.manage"))


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None) if actor is not None else None


def active_policy() -> CmsPolicy | None:
    return CmsPolicy.objects.filter(is_active=True).order_by("-version").first()


def categories_for(actor, *, include_inactive: bool = False) -> QuerySet[ComplaintCategory]:
    base = ComplaintCategory.objects.all()
    if include_inactive and _is_admin(actor):
        return base
    return base.filter(is_active=True)


def complaints_for(actor) -> QuerySet[Complaint]:
    # UC-CMS-002, UC-CMS-003, UC-CMS-012, AFR-CMS-016..018, AFR-CMS-040: role-scoped queryset.
    base = Complaint.objects.select_related("category", "policy")
    if actor is None:
        return base.none()
    if _is_handler(actor) or _is_supervisor(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()


def reopen_requests_for(actor) -> QuerySet[ReopenRequest]:
    # UC-CMS-020, BR-CMS-019: supervisor sees all reopen requests; complainants see only own.
    base = ReopenRequest.objects.select_related("complaint", "complaint__category")
    if actor is None:
        return base.none()
    if actor.has_permission("cms.reopen_request.approve"):
        return base
    own = _own_id(actor)
    return base.filter(requested_by_user_id=own) if own is not None else base.none()


def feedback_for(actor) -> QuerySet[ComplaintFeedback]:
    # UC-CMS-010, BR-CMS-023, AFR-CMS-036, AFR-CMS-037: review all or own.
    base = ComplaintFeedback.objects.select_related("complaint", "complaint__category")
    if actor is None:
        return base.none()
    if actor.has_permission("cms.feedback.review"):
        return base
    own = _own_id(actor)
    return base.filter(submitted_by_user_id=own) if own is not None else base.none()


def announcements_for(actor) -> QuerySet[ComplaintAnnouncement]:
    # UC-CMS-014, AFR-CMS-047: published active announcements visible to authorized viewers.
    base = ComplaintAnnouncement.objects.all()
    if actor is None:
        return base.none()
    if actor.has_permission("cms.announcement.publish"):
        return base
    return base.filter(is_active=True)
