import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.cms.domain.state_machine import CLOSED, RESOLVED
from modules.cms.models import (
    Complaint,
    ComplaintAnnouncement,
    ComplaintFeedback,
    ReopenRequest,
)
from modules.cms.tests.conftest import auth_client

pytestmark = pytest.mark.django_db


def _seed_rows(policy, category, count: int, start_idx: int):
    for i in range(start_idx, start_idx + count):
        c = Complaint.objects.create(
            tracking_code=f"CMS-QB{i:05d}",
            user_id=1000 + i,
            category=category,
            policy=policy,
            title=f"Complaint {i}",
            description="Body",
            status=CLOSED if i % 2 == 0 else RESOLVED,
        )
        ComplaintFeedback.objects.create(
            complaint=c, submitted_by_user_id=1000 + i, rating=4, comment="OK"
        )
        if c.status == CLOSED:
            ReopenRequest.objects.create(
                complaint=c, requested_by_user_id=1000 + i, reason="Check"
            )
        ComplaintAnnouncement.objects.create(
            title=f"Notice {i}",
            body="Text",
            published_by_user_id=202,
            published_by_role="Complaint Handler",
            published_at=timezone.now(),
        )


def _count_queries(client, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(url)
    assert resp.status_code == 200
    return len(ctx)


def test_list_endpoints_query_counts_constant_between_2_and_20_rows(
    stub_iam, cms_policy, cms_category
):
    # Step 5.8: query count must not grow between 2 rows and 20 rows (zero N+1).
    _seed_rows(cms_policy, cms_category, count=2, start_idx=1)

    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    q_complaints_2 = _count_queries(handler, "/api/v1/cms/complaints/")
    q_feedback_2 = _count_queries(handler, "/api/v1/cms/feedback/")
    q_announce_2 = _count_queries(handler, "/api/v1/cms/announcements/")

    sup = auth_client(stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty")
    q_reopen_2 = _count_queries(sup, "/api/v1/cms/reopen-requests/")

    _seed_rows(cms_policy, cms_category, count=18, start_idx=3)

    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert _count_queries(handler, "/api/v1/cms/complaints/") == q_complaints_2
    assert _count_queries(handler, "/api/v1/cms/feedback/") == q_feedback_2
    assert _count_queries(handler, "/api/v1/cms/announcements/") == q_announce_2

    sup = auth_client(stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty")
    assert _count_queries(sup, "/api/v1/cms/reopen-requests/") == q_reopen_2
