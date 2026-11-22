from __future__ import annotations

from django.db.models import Avg, Count, Q
from django.utils import timezone

from modules.cms.domain.state_machine import (
    CLOSED,
    ESCALATION_AUTOMATIC,
    ESCALATION_MANUAL,
    IN_PROGRESS,
    REJECTED,
    RESOLVED,
    SUBMITTED,
)
from modules.cms.models import Complaint, ComplaintFeedback


def operational_report() -> dict:
    # UC-CMS-015, BR-CMS-032, AFR-CMS-049: handler operational counts.
    now = timezone.now()
    agg = Complaint.objects.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status=SUBMITTED)),
        in_progress=Count("id", filter=Q(status=IN_PROGRESS)),
        resolved=Count("id", filter=Q(status=RESOLVED)),
        rejected=Count("id", filter=Q(status=REJECTED)),
        closed=Count("id", filter=Q(status=CLOSED)),
        escalated=Count("id", filter=Q(is_escalated=True)),
        overdue=Count("id", filter=Q(status__in=[SUBMITTED, IN_PROGRESS], sla_due_at__lt=now)),
    )
    by_category = list(
        Complaint.objects.values("category__code", "category__name")
        .annotate(count=Count("id"))
        .order_by("-count", "category__name")
    )
    by_priority = list(
        Complaint.objects.values("priority").annotate(count=Count("id")).order_by("priority")
    )
    return {
        "counts": agg,
        "by_category": [
            {"code": r["category__code"], "name": r["category__name"], "count": r["count"]}
            for r in by_category
        ],
        "by_priority": [
            {"priority": r["priority"] or "Unassigned", "count": r["count"]}
            for r in by_priority
        ],
    }


def escalation_summary() -> dict:
    # UC-CMS-016, BR-CMS-032, AFR-CMS-050, AFR-CMS-051: supervisor escalation & complaint summaries.
    agg = Complaint.objects.aggregate(
        total_complaints=Count("id"),
        open_complaints=Count("id", filter=Q(status__in=[SUBMITTED, IN_PROGRESS])),
        total_escalated=Count("id", filter=Q(is_escalated=True)),
        manual_escalated=Count(
            "id", filter=Q(is_escalated=True, escalation_type=ESCALATION_MANUAL)
        ),
        automatic_escalated=Count(
            "id", filter=Q(is_escalated=True, escalation_type=ESCALATION_AUTOMATIC)
        ),
        unresolved_escalated=Count(
            "id", filter=Q(is_escalated=True, status__in=[SUBMITTED, IN_PROGRESS])
        ),
        closed_escalated=Count("id", filter=Q(is_escalated=True, status=CLOSED)),
    )
    by_category = list(
        Complaint.objects.filter(is_escalated=True)
        .values("category__code", "category__name")
        .annotate(count=Count("id"))
        .order_by("-count", "category__name")
    )
    return {
        "summary": agg,
        "escalated_by_category": [
            {"code": r["category__code"], "name": r["category__name"], "count": r["count"]}
            for r in by_category
        ],
    }


def analytics_summary() -> dict:
    # UC-CMS-017, BR-CMS-032, BR-CMS-033, AFR-CMS-052..054: system admin CMS analytics.
    op = operational_report()
    esc = escalation_summary()
    fb = ComplaintFeedback.objects.aggregate(
        feedback_count=Count("id"),
        average_rating=Avg("rating"),
    )
    return {
        "counts": op["counts"],
        "escalations": esc["summary"],
        "by_category": op["by_category"],
        "by_priority": op["by_priority"],
        "feedback": {
            "count": fb["feedback_count"],
            "average_rating": round(float(fb["average_rating"]), 2)
            if fb["average_rating"] is not None
            else None,
        },
    }
