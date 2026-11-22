from io import StringIO

import pytest
from django.core.management import call_command

from modules.cms.contracts import get_complaint_summaries
from modules.cms.models import (
    CmsNotificationEvent,
    Complaint,
    ComplaintCategory,
    ComplaintHistory,
)
from modules.cms.registry import readiness
from modules.cms.tests.conftest import auth_client

pytestmark = pytest.mark.django_db

VALID_DRIVE_URL = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view"


def test_ordinary_plain_student_lifecycle_bw_cms_01_02_cw_cms_01(
    stub_iam, cms_policy, cms_category, cms_category_alt
):
    # Step 5.2, UC-CMS-001..007, UC-CMS-009, UC-CMS-010, BW-CMS-01, BW-CMS-02, CW-CMS-01, CFR-CMS-001..005, CFR-CMS-007.
    # AFR-CMS-001..023, AFR-CMS-025..027, AFR-CMS-029, AFR-CMS-035..037, AFR-CMS-055..057, AFR-CMS-061, AFR-CMS-063.
    student = auth_client(stub_iam, user_id=101, role="student")

    # Plain user with no optional attachments submits complaint (UC-CMS-001, BR-CMS-001..006).
    r_sub = student.post(
        "/api/v1/cms/complaints/",
        {
            "category_id": cms_category.id,
            "title": "Wi-Fi dead in room 204",
            "description": "No Wi-Fi signal since morning.",
            "attachments": [{"label": "router_photo.jpg", "url": VALID_DRIVE_URL}],
        },
        format="json",
    )
    assert r_sub.status_code == 201
    cid = r_sub.data["id"]
    assert r_sub.data["status"] == "submitted"
    assert r_sub.data["tracking_code"].startswith("CMS-")
    assert len(r_sub.data["attachments"]) == 1
    assert CmsNotificationEvent.objects.filter(
        complaint_id=cid, event_type="complaint_submitted"
    ).exists()

    # Complainant tracks own complaint & history (UC-CMS-002, BR-CMS-011).
    r_track = student.get(f"/api/v1/cms/complaints/{cid}/")
    assert r_track.status_code == 200
    assert len(r_track.data["history"]) == 1

    # Handler reviews worklist, sets up manual assignment, category, priority (UC-CMS-003, UC-CMS-004, BR-CMS-007..010).
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert len(handler.get("/api/v1/cms/complaints/").data["results"]) == 1

    # Cannot update progress before handling setup (guard check).
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{cid}/progress/", {"note": "Checking"}, format="json"
        ).status_code
        == 422
    )

    r_setup = handler.post(
        f"/api/v1/cms/complaints/{cid}/handling-setup/",
        {
            "category_id": cms_category_alt.id,
            "priority": "High",
            "assigned_unit": "Network Operations",
        },
        format="json",
    )
    assert r_setup.status_code == 200
    assert r_setup.data["priority"] == "High"
    assert r_setup.data["sla_due_at"] is not None

    # Handler updates progress (UC-CMS-005, BR-CMS-011, BR-CMS-015, ISS-CMS-007).
    r_prog = handler.post(
        f"/api/v1/cms/complaints/{cid}/progress/",
        {"note": "Technician dispatched to inspect access point."},
        format="json",
    )
    assert r_prog.status_code == 200
    assert r_prog.data["status"] == "in_progress"

    # Handler resolves with details (UC-CMS-006, BR-CMS-013, BR-CMS-015).
    r_res = handler.post(
        f"/api/v1/cms/complaints/{cid}/resolve/",
        {"resolution_details": "Replaced faulty AP on 2nd floor."},
        format="json",
    )
    assert r_res.status_code == 200
    assert r_res.data["status"] == "resolved"

    # Routine complaint requires Complainant verification, not Supervisor (UC-CMS-007, BR-CMS-016, ISS-CMS-010).
    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    assert (
        supervisor.post(
            f"/api/v1/cms/complaints/{cid}/verify-close/", {}, format="json"
        ).status_code
        == 422
    )

    student = auth_client(stub_iam, user_id=101, role="student")
    r_close = student.post(
        f"/api/v1/cms/complaints/{cid}/verify-close/", {"note": "Working now"}, format="json"
    )
    assert r_close.status_code == 200
    assert r_close.data["status"] == "closed"

    # Complainant submits feedback (UC-CMS-009, BR-CMS-022).
    r_fb = student.post(
        f"/api/v1/cms/complaints/{cid}/feedback/",
        {"rating": 5, "comment": "Quick fix"},
        format="json",
    )
    assert r_fb.status_code == 201
    # Duplicate feedback refused (409).
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/feedback/", {"rating": 4}, format="json"
        ).status_code
        == 409
    )

    # Handler and Supervisor review feedback (UC-CMS-010, BR-CMS-023).
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert len(handler.get("/api/v1/cms/feedback/").data["results"]) == 1
    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    assert len(supervisor.get("/api/v1/cms/feedback/").data["results"]) == 1

    # Plural contract check.
    summaries = get_complaint_summaries([101, 999])
    assert summaries[101].total_complaints == 1
    assert summaries[999].total_complaints == 0


def test_rejection_and_invalid_submission_flows_bw_cms_04(stub_iam, cms_policy, cms_category):
    # UC-CMS-001 (E1, E2), UC-CMS-006 (Reject), BW-CMS-04, BR-CMS-002, BR-CMS-004, BR-CMS-014, AFR-CMS-024, AFR-CMS-058.
    student = auth_client(stub_iam, user_id=101, role="student")

    # Missing fields & invalid Drive link refused.
    assert student.post(
        "/api/v1/cms/complaints/",
        {"category_id": cms_category.id, "title": " ", "description": "d"},
        format="json",
    ).status_code in (400, 422)
    assert (
        student.post(
            "/api/v1/cms/complaints/",
            {
                "category_id": cms_category.id,
                "title": "Bad link",
                "description": "d",
                "attachments": [{"url": "https://evil.example/a"}],
            },
            format="json",
        ).status_code
        == 422
    )

    # Valid submission then Handler rejects with reason.
    cid = student.post(
        "/api/v1/cms/complaints/",
        {
            "category_id": cms_category.id,
            "title": "Personal phone",
            "description": "Cracked screen",
        },
        format="json",
    ).data["id"]

    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    r_rej = handler.post(
        f"/api/v1/cms/complaints/{cid}/reject/",
        {"rejection_reason": "Outside institutional scope"},
        format="json",
    )
    assert r_rej.status_code == 200
    assert r_rej.data["status"] == "rejected"
    # Terminal state cannot be modified further (Step 5.11).
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{cid}/resolve/",
            {"resolution_details": "Nope"},
            format="json",
        ).status_code
        == 409
    )
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{cid}/escalate/", {"reason": "Nope"}, format="json"
        ).status_code
        == 409
    )


def test_escalation_supervisor_verification_and_reopening_bw_cms_03_05_06_07_cw_cms_02_03(
    stub_iam, cms_policy, cms_category
):
    # UC-CMS-008, UC-CMS-011, UC-CMS-012, UC-CMS-019, UC-CMS-020, BW-CMS-03, BW-CMS-05, BW-CMS-06, BW-CMS-07, CW-CMS-02, CW-CMS-03.
    # CFR-CMS-005, CFR-CMS-006, CFR-CMS-008, AFR-CMS-028, AFR-CMS-030..034, AFR-CMS-038..040, AFR-CMS-059, AFR-CMS-060.
    # BR-CMS-016..021, BR-CMS-024, BR-CMS-025.
    student = auth_client(stub_iam, user_id=101, role="student")
    cid = student.post(
        "/api/v1/cms/complaints/",
        {
            "category_id": cms_category.id,
            "title": "Main switchboard fault",
            "description": "Power tripping",
        },
        format="json",
    ).data["id"]

    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    handler.post(
        f"/api/v1/cms/complaints/{cid}/handling-setup/",
        {"priority": "High", "assigned_to_user_id": 202},
        format="json",
    )
    r_esc = handler.post(
        f"/api/v1/cms/complaints/{cid}/escalate/",
        {"reason": "Requires vendor approval"},
        format="json",
    )
    assert r_esc.status_code == 200
    assert r_esc.data["is_escalated"] is True
    assert r_esc.data["escalation_type"] == "manual"
    # Double escalation refused.
    assert (
        handler.post(
            f"/api/v1/cms/complaints/{cid}/escalate/", {"reason": "Again"}, format="json"
        ).status_code
        == 409
    )

    # Supervisor monitors escalated complaints (UC-CMS-012).
    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    r_mon = supervisor.get("/api/v1/cms/complaints/?escalated=true")
    assert r_mon.status_code == 200
    assert len(r_mon.data["results"]) == 1

    # Handler resolves escalated complaint; Supervisor verifies closure (UC-CMS-019, BW-CMS-03).
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    handler.post(
        f"/api/v1/cms/complaints/{cid}/resolve/",
        {"resolution_details": "Vendor replaced breaker"},
        format="json",
    )

    student = auth_client(stub_iam, user_id=101, role="student")
    assert (
        student.post(
            f"/api/v1/cms/complaints/{cid}/verify-close/", {}, format="json"
        ).status_code
        == 422
    )

    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    r_sclose = supervisor.post(
        f"/api/v1/cms/complaints/{cid}/verify-close/",
        {"note": "Supervisor verified"},
        format="json",
    )
    assert r_sclose.status_code == 200
    assert r_sclose.data["status"] == "closed"

    # Reopen request denied (UC-CMS-008, UC-CMS-020, BW-CMS-06).
    student = auth_client(stub_iam, user_id=101, role="student")
    r_req1 = student.post(
        f"/api/v1/cms/complaints/{cid}/reopen-requests/",
        {"reason": "Still noisy"},
        format="json",
    )
    assert r_req1.status_code == 201
    req1_id = r_req1.data["id"]

    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    assert (
        len(supervisor.get("/api/v1/cms/reopen-requests/?status=pending").data["results"]) == 1
    )
    r_deny = supervisor.post(
        f"/api/v1/cms/reopen-requests/{req1_id}/decide/",
        {"decision": "deny", "decision_note": "Normal hum"},
        format="json",
    )
    assert r_deny.status_code == 200
    assert r_deny.data["status"] == "denied"
    assert Complaint.objects.get(pk=cid).status == "closed"

    # Reopen request approved (UC-CMS-020, BW-CMS-05, ISS-CMS-008).
    student = auth_client(stub_iam, user_id=101, role="student")
    req2_id = student.post(
        f"/api/v1/cms/complaints/{cid}/reopen-requests/",
        {"reason": "Tripped again"},
        format="json",
    ).data["id"]
    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    r_app = supervisor.post(
        f"/api/v1/cms/reopen-requests/{req2_id}/decide/",
        {"decision": "approve", "decision_note": "Reopening"},
        format="json",
    )
    assert r_app.status_code == 200
    assert r_app.data["status"] == "approved"
    reopened = Complaint.objects.get(pk=cid)
    assert reopened.status == "in_progress"
    assert reopened.reopen_count == 1
    assert ComplaintHistory.objects.filter(
        complaint=reopened, event_type="reopen_approved"
    ).exists()


def test_announcements_reports_policy_and_management_commands(
    stub_iam, cms_policy, cms_category
):
    # UC-CMS-013, UC-CMS-014, UC-CMS-015, UC-CMS-016, UC-CMS-017, CFR-CMS-010, CFR-CMS-011, CFR-CMS-014.
    # AFR-CMS-045..054, AFR-CMS-062, AFR-CMS-069..073, BR-CMS-030..033, BR-CMS-038..041.
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    r_ann = handler.post(
        "/api/v1/cms/announcements/",
        {"title": "Scheduled Water Maintenance", "body": "Water off from 2-4 PM."},
        format="json",
    )
    assert r_ann.status_code == 201
    assert CmsNotificationEvent.objects.filter(event_type="announcement_published").exists()

    student = auth_client(stub_iam, user_id=101, role="student")
    r_view_ann = student.get("/api/v1/cms/announcements/")
    assert r_view_ann.status_code == 200
    assert len(r_view_ann.data["results"]) == 1

    # Role-scoped reports (UC-CMS-015, UC-CMS-016, UC-CMS-017).
    handler = auth_client(stub_iam, user_id=202, role="Complaint Handler", kind="staff")
    assert handler.get("/api/v1/cms/reports/operational/").status_code == 200

    supervisor = auth_client(
        stub_iam, user_id=303, role="Complaint Supervisor", kind="faculty"
    )
    assert supervisor.get("/api/v1/cms/reports/escalations/").status_code == 200

    admin = auth_client(stub_iam, user_id=404, role="adminstrator", kind="staff")
    assert admin.get("/api/v1/cms/reports/analytics/").status_code == 200
    r_cat = admin.post(
        "/api/v1/cms/categories/", {"code": "HOST", "name": "Hostel"}, format="json"
    )
    assert r_cat.status_code == 201
    assert (
        admin.post(
            "/api/v1/cms/categories/", {"code": "HOST", "name": "Dup"}, format="json"
        ).status_code
        == 409
    )

    r_pol = admin.post(
        "/api/v1/cms/policy/",
        {
            "low_sla_hours": 96,
            "medium_sla_hours": 48,
            "high_sla_hours": 12,
            "reminder_lead_hours": 2,
            "max_attachments": 4,
            "routine_verification_by": "complainant",
            "escalated_verification_by": "supervisor",
            "notify_on_announcement": False,
        },
        format="json",
    )
    assert r_pol.status_code == 201
    assert r_pol.data["version"] == 2
    assert len(admin.get("/api/v1/cms/policy/").data["results"]) == 2

    # Management commands work cleanly.
    out = StringIO()
    call_command("seed_cms_policy", stdout=out)
    call_command("check_cms_readiness", stdout=out)
    call_command("run_cms_sla_tasks", stdout=out)
    assert "CMS readiness: OK" in out.getvalue()
    assert readiness() == []


def test_unseeded_policy_fails_gracefully_with_422_and_readiness_names_remediation(stub_iam):
    # Step 2.8, Step 7.5: missing policy never 500s; readiness reports what to run.
    unmet = readiness()
    assert len(unmet) == 2
    assert "seed_cms_policy" in unmet[0]

    cat = ComplaintCategory.objects.create(code="TEST", name="Test Cat")
    student = auth_client(stub_iam, user_id=101, role="student")
    resp = student.post(
        "/api/v1/cms/complaints/",
        {"category_id": cat.id, "title": "Unseeded test", "description": "No policy yet"},
        format="json",
    )
    assert resp.status_code == 422
    assert resp.data["error"]["code"] == "cms_policy_not_configured"
