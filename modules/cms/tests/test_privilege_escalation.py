import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.cms.models import Complaint
from modules.cms.registry import NAV_ITEMS, PERMISSIONS, ROLE_GRANTS, SYSTEM_PERMISSIONS
from modules.cms.tests.conftest import auth_client

pytestmark = pytest.mark.django_db


def test_registry_permissions_and_role_grants_have_no_drift():
    # Step 5.1: every permission in ROLE_GRANTS, NAV_ITEMS, and SYSTEM_PERMISSIONS must be declared.
    declared = {code for code, _ in PERMISSIONS}
    closed_verbs = {
        "view",
        "create",
        "update",
        "delete",
        "approve",
        "publish",
        "review",
        "assign",
        "revoke",
        "export",
        "import",
        "restore",
        "manage",
    }
    for code in declared:
        parts = code.split(".")
        assert len(parts) == 3 and parts[0] == "cms"
        assert parts[2] in closed_verbs
    for perm in SYSTEM_PERMISSIONS:
        assert perm in declared
    for role, grants in ROLE_GRANTS.items():
        for code in grants:
            assert code in declared, f"Role {role} uses undeclared permission {code}"
    for item in NAV_ITEMS:
        assert item["required_permission"] in declared


def test_both_gates_separately_and_unauthenticated_401(stub_iam, cms_policy, cms_category):
    # Step 5.1, Step 5.5, Step 7.7: 401 unauthenticated, 403 without module grant, 403 without permission.
    anon = APIClient()
    assert anon.get("/api/v1/cms/complaints/").status_code == 401

    # Has permission, lacks module grant.
    c_no_mod = auth_client(
        stub_iam, user_id=11, role="student", permissions=["cms.complaint.view"], modules=()
    )
    assert c_no_mod.get("/api/v1/cms/complaints/").status_code == 403

    # Has module grant, lacks permission.
    c_no_perm = auth_client(
        stub_iam, user_id=12, role="student", permissions=[], modules=("cms",)
    )
    assert c_no_perm.get("/api/v1/cms/complaints/").status_code == 403


def test_complainant_cannot_reach_handler_supervisor_or_admin_endpoints(
    stub_iam, cms_policy, cms_category
):
    # Step 5.5, BR-CMS-019, BR-CMS-030, BR-CMS-032: privilege escalation checks for complainant.
    student = auth_client(stub_iam, user_id=101, role="student")
    created = student.post(
        "/api/v1/cms/complaints/",
        {"category_id": cms_category.id, "title": "Leak", "description": "Pipe leak"},
        format="json",
    )
    assert created.status_code == 201
    cid = created.data["id"]

    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/handling-setup/",
            {"priority": "High", "assigned_unit": "Civil"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/progress/", {"note": "hack"}, format="json"
        ).status_code
        == 403
    )
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/resolve/",
            {"resolution_details": "hack"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/reject/",
            {"rejection_reason": "hack"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/escalate/", {"reason": "hack"}, format="json"
        ).status_code
        == 403
    )
    assert student.get("/api/v1/cms/reopen-requests/").status_code == 403
    assert student.get("/api/v1/cms/feedback/").status_code == 403
    assert (
        student.post(
            "/api/v1/cms/announcements/", {"title": "Fake", "body": "Body"}, format="json"
        ).status_code
        == 403
    )
    assert student.get("/api/v1/cms/reports/operational/").status_code == 403
    assert student.get("/api/v1/cms/reports/escalations/").status_code == 403
    assert student.get("/api/v1/cms/reports/analytics/").status_code == 403
    assert student.get("/api/v1/cms/policy/").status_code == 403
    assert (
        student.post(
            "/api/v1/cms/categories/", {"code": "HACK", "name": "Hack"}, format="json"
        ).status_code
        == 403
    )


def test_role_boundaries_handler_supervisor_admin_and_self_action(
    stub_iam, cms_policy, cms_category
):
    # Step 5.11, BR-CMS-019, BR-CMS-032: handler/supervisor/admin boundaries and self-approval refusal.
    # Handler cannot approve reopen requests or manage policy or view supervisor/admin reports.
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert handler.get("/api/v1/cms/reopen-requests/").status_code == 403
    assert handler.get("/api/v1/cms/reports/escalations/").status_code == 403
    assert handler.get("/api/v1/cms/reports/analytics/").status_code == 403
    assert handler.get("/api/v1/cms/policy/").status_code == 403

    # Supervisor cannot perform routine complaint handling setup, progress, resolution, or admin analytics.
    c = Complaint.objects.create(
        tracking_code="CMS-SELF0001",
        user_id=202,
        category=cms_category,
        policy=cms_policy,
        title="Own ticket",
        description="Filed by handler themselves",
    )
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{c.id}/handling-setup/",
            {"priority": "Low", "assigned_unit": "IT"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{c.id}/reject/",
            {"rejection_reason": "Self reject"},
            format="json",
        ).status_code
        == 403
    )

    sup = auth_client(stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty")
    assert (
        sup.post(
            f"/api/v1/cms/complaints/{c.id}/resolve/",
            {"resolution_details": "No"},
            format="json",
        ).status_code
        == 403
    )
    assert sup.get("/api/v1/cms/reports/operational/").status_code == 403
    assert sup.get("/api/v1/cms/reports/analytics/").status_code == 403

    # System Admin cannot submit complaints or resolve them.
    admin = auth_client(stub_iam, user_id=404, role="adminstrator", kind="staff")
    assert (
        admin.post(
            "/api/v1/cms/complaints/",
            {"category_id": cms_category.id, "title": "A", "description": "B"},
            format="json",
        ).status_code
        == 403
    )
    assert admin.get("/api/v1/cms/reports/analytics/").status_code == 200


def test_role_switch_sees_only_active_role(stub_iam, cms_policy, cms_category):
    # Step 5.1: user holding both student and Complaint Handler gets only the acting role's permissions.
    dual_as_student = auth_client(
        stub_iam,
        user_id=505,
        role="student",
        roles=("student", "Complaint Handler"),
        permissions=ROLE_GRANTS["student"],
    )
    assert dual_as_student.get("/api/v1/cms/reports/operational/").status_code == 403

    dual_as_handler = auth_client(
        stub_iam,
        user_id=505,
        role="Complaint Handler",
        roles=("student", "Complaint Handler"),
        permissions=ROLE_GRANTS["Complaint Handler"],
    )
    assert dual_as_handler.get("/api/v1/cms/reports/operational/").status_code == 200


def test_cookie_authenticated_write_requires_csrf_token(stub_iam, cms_policy, cms_category):
    # Step 7.7: cookie-authenticated write without X-CSRF-Token returns 403.
    stub_iam(
        make_session(
            user_id=101,
            kind="student",
            active_role="student",
            roles=("student",),
            permissions=tuple(ROLE_GRANTS["student"]),
            modules=("cms",),
        )
    )
    client = APIClient()
    client.cookies["fusion_session"] = "sess-123"
    resp = client.post(
        "/api/v1/cms/complaints/",
        {"category_id": cms_category.id, "title": "CSRF test", "description": "No token"},
        format="json",
    )
    assert resp.status_code == 403
