from __future__ import annotations

MODULE = {
    "code": "cms",
    "label": "Complaints",
    "icon": "WarningCircle",
    "base_path": "/cms",
    "nav_section": "Services",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "cms.complaints",
        "label": "Complaints",
        "icon": "ClipboardText",
        "to": "/cms/complaints",
        "required_permission": "cms.complaint.view",
        "sort_order": 10,
    },
    {
        "code": "cms.escalations",
        "label": "Escalations",
        "icon": "Warning",
        "to": "/cms/escalations",
        "required_permission": "cms.escalation.view",
        "sort_order": 20,
    },
    {
        "code": "cms.reopen_requests",
        "label": "Reopen Requests",
        "icon": "ArrowCounterClockwise",
        "to": "/cms/reopen-requests",
        "required_permission": "cms.reopen_request.approve",
        "sort_order": 30,
    },
    {
        "code": "cms.feedback",
        "label": "Feedback",
        "icon": "Star",
        "to": "/cms/feedback",
        "required_permission": "cms.feedback.review",
        "sort_order": 40,
    },
    {
        "code": "cms.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/cms/announcements",
        "required_permission": "cms.announcement.view",
        "sort_order": 50,
    },
    {
        "code": "cms.reports",
        "label": "Reports & Analytics",
        "icon": "ChartBar",
        "to": "/cms/reports",
        "required_permission": "cms.report.view",
        "sort_order": 60,
    },
    {
        "code": "cms.policy",
        "label": "CMS Policy",
        "icon": "SlidersHorizontal",
        "to": "/cms/policy",
        "required_permission": "cms.policy.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("cms.complaint.view", "View complaints within the caller's role scope"),
    ("cms.complaint.create", "Submit a new complaint"),
    ("cms.complaint.assign", "Manually assign, categorize, and prioritize a complaint"),
    (
        "cms.complaint.update",
        "Update complaint progress, resolve, reject, or escalate a complaint",
    ),
    ("cms.complaint.approve", "Verify a resolved complaint for closure"),
    ("cms.reopen_request.create", "Request reopening of a closed complaint"),
    ("cms.reopen_request.approve", "Review and approve or deny complaint reopening requests"),
    ("cms.feedback.create", "Submit feedback on a resolved or closed complaint"),
    ("cms.feedback.review", "Review submitted complaint feedback"),
    ("cms.escalation.view", "Monitor escalated complaints"),
    ("cms.announcement.view", "View complaint-related announcements"),
    ("cms.announcement.publish", "Publish complaint-related announcements"),
    ("cms.report.view", "View role-appropriate complaint reports, summaries, and analytics"),
    (
        "cms.policy.manage",
        "Manage complaint categories and effective-dated SLA/attachment policy",
    ),
    ("cms.sla.update", "System SLA pre-breach reminder and automatic breach escalation"),
]

SYSTEM_PERMISSIONS = [
    "cms.sla.update",
]

_COMPLAINANT = [
    "cms.complaint.view",
    "cms.complaint.create",
    "cms.complaint.approve",
    "cms.reopen_request.create",
    "cms.feedback.create",
    "cms.announcement.view",
]

_HANDLER = [
    "cms.complaint.view",
    "cms.complaint.assign",
    "cms.complaint.update",
    "cms.feedback.review",
    "cms.announcement.view",
    "cms.announcement.publish",
    "cms.report.view",
]

_SUPERVISOR = [
    "cms.complaint.view",
    "cms.complaint.approve",
    "cms.reopen_request.approve",
    "cms.feedback.review",
    "cms.escalation.view",
    "cms.announcement.view",
    "cms.announcement.publish",
    "cms.report.view",
]

_SYSTEM_ADMIN = [
    "cms.report.view",
    "cms.policy.manage",
]

ROLE_GRANTS = {
    "student": _COMPLAINANT,
    "faculty": _COMPLAINANT,
    "staff": _COMPLAINANT,
    "Complaint Handler": _HANDLER,
    "Complaint Supervisor": _SUPERVISOR,
    "adminstrator": _SYSTEM_ADMIN,
}


def readiness() -> list[str]:
    # Step 7.5: return unmet prerequisites with clear remediation commands.
    from modules.cms.models import CmsPolicy, ComplaintCategory

    unmet: list[str] = []
    if not CmsPolicy.objects.filter(is_active=True).exists():
        unmet.append(
            "No active CMS policy exists — run '.venv/bin/python manage.py seed_cms_policy'."
        )
    if not ComplaintCategory.objects.filter(is_active=True).exists():
        unmet.append(
            "No active CMS categories — run manage.py seed_cms_policy."
        )
    return unmet
