import pytest

from modules.cms.models import Complaint
from modules.cms.tests.conftest import auth_client

pytestmark = pytest.mark.django_db


def test_complainant_isolation_returns_404_never_403(stub_iam, cms_policy, cms_category):
    # Step 2.5, Step 5.6, UC-CMS-002, AFR-CMS-016, AFR-CMS-017: user B cannot see or act on user A's complaint.
    user_a = auth_client(stub_iam, user_id=101, role="student")
    created = user_a.post(
        "/api/v1/cms/complaints/",
        {
            "category_id": cms_category.id,
            "title": "Private Room 204 Issue",
            "description": "Sensitive details",
        },
        format="json",
    )
    assert created.status_code == 201
    cid = created.data["id"]
    tracking = created.data["tracking_code"]

    user_b = auth_client(stub_iam, user_id=102, role="student")
    # List and search filter must not reveal A's row.
    lst = user_b.get(f"/api/v1/cms/complaints/?search={tracking}")
    assert lst.status_code == 200
    assert lst.data["results"] == []

    # Direct detail read yields 404, not 403.
    assert user_b.get(f"/api/v1/cms/complaints/{cid}/").status_code == 404

    # Direct write actions on A's complaint yield 404.
    Complaint.objects.filter(pk=cid).update(status="resolved")
    assert (
        user_b.post(
            f"/api/v1/cms/complaints/{cid}/verify-close/", {}, format="json"
        ).status_code
        == 404
    )
    assert (
        user_b.post(
            f"/api/v1/cms/complaints/{cid}/feedback/", {"rating": 1}, format="json"
        ).status_code
        == 404
    )
    Complaint.objects.filter(pk=cid).update(status="closed")
    assert (
        user_b.post(
            f"/api/v1/cms/complaints/{cid}/reopen-requests/",
            {"reason": "Hijack"},
            format="json",
        ).status_code
        == 404
    )


def test_bad_query_parameters_return_400_never_500(stub_iam, cms_policy, cms_category):
    # Step 4.5, Step 5.11: hostile query params return 400.
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert handler.get("/api/v1/cms/complaints/?status=bogus").status_code == 400
    assert handler.get("/api/v1/cms/complaints/?priority=Urgent").status_code == 400
    assert handler.get("/api/v1/cms/complaints/?escalated=maybe").status_code == 400
    assert handler.get("/api/v1/cms/complaints/?category_id=abc").status_code == 400

    sup = auth_client(stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty")
    assert sup.get("/api/v1/cms/reopen-requests/?status=invalid").status_code == 400
