from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Q

from modules.cms.domain.state_machine import IN_PROGRESS, RESOLVED, SUBMITTED
from modules.cms.models import Complaint


@dataclass(frozen=True)
class ComplaintSummaryDTO:
    user_id: int
    total_complaints: int
    open_complaints: int
    resolved_complaints: int
    escalated_complaints: int


def get_complaint_summaries(user_ids: Sequence[int]) -> dict[int, ComplaintSummaryDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (
        Complaint.objects.filter(user_id__in=ids)
        .values("user_id")
        .annotate(
            total=Count("id"),
            open_count=Count("id", filter=Q(status__in=[SUBMITTED, IN_PROGRESS])),
            resolved_count=Count("id", filter=Q(status=RESOLVED)),
            escalated_count=Count("id", filter=Q(is_escalated=True)),
        )
    )
    by_uid = {r["user_id"]: r for r in rows}
    return {
        uid: ComplaintSummaryDTO(
            user_id=uid,
            total_complaints=by_uid.get(uid, {}).get("total", 0),
            open_complaints=by_uid.get(uid, {}).get("open_count", 0),
            resolved_complaints=by_uid.get(uid, {}).get("resolved_count", 0),
            escalated_complaints=by_uid.get(uid, {}).get("escalated_count", 0),
        )
        for uid in ids
    }
