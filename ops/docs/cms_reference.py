#!/usr/bin/env python
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "19-cms" / "cms-reference.md"

MAPPINGS: list[tuple[str, str, str]] = [
    ("BR-CMS-001", "modules/cms/services/complaints.py", "def submit_complaint("),
    ("BR-CMS-002", "modules/cms/domain/rules.py", "def validate_submission("),
    ("BR-CMS-003", "modules/cms/models/complaint.py", "class Complaint("),
    ("BR-CMS-004", "modules/cms/domain/rules.py", "def validate_attachment_count("),
    ("BR-CMS-005", "modules/cms/models/policy.py", "class CmsPolicy("),
    ("BR-CMS-006", "modules/cms/models/complaint.py", "cms_complaint_tracking_code_uniq"),
    ("BR-CMS-007", "modules/cms/services/handling.py", "def setup_complaint_handling("),
    ("BR-CMS-008", "modules/cms/models/policy.py", "class ComplaintCategory("),
    ("BR-CMS-009", "modules/cms/domain/rules.py", "def validate_priority("),
    (
        "BR-CMS-010",
        "modules/cms/services/handling.py",
        "complaint.sla_due_at = compute_sla_due_at(",
    ),
    ("BR-CMS-011", "modules/cms/models/complaint.py", "class ComplaintHistory("),
    ("BR-CMS-012", "modules/cms/domain/state_machine.py", "TRANSITIONS:"),
    ("BR-CMS-013", "modules/cms/services/transitions.py", "def resolve_complaint("),
    ("BR-CMS-014", "modules/cms/services/transitions.py", "def reject_complaint("),
    ("BR-CMS-015", "modules/cms/services/notifications.py", "def enqueue_notification("),
    ("BR-CMS-016", "modules/cms/domain/rules.py", "def required_verifier("),
    ("BR-CMS-017", "modules/cms/services/transitions.py", "def verify_and_close_complaint("),
    ("BR-CMS-018", "modules/cms/domain/rules.py", "def validate_reopen_request("),
    ("BR-CMS-019", "modules/cms/services/reopening.py", "def decide_reopening("),
    ("BR-CMS-020", "modules/cms/services/reopening.py", "complaint.reopen_count += 1"),
    ("BR-CMS-021", "modules/cms/models/reopening.py", "class ReopenRequest("),
    ("BR-CMS-022", "modules/cms/domain/rules.py", "def validate_feedback("),
    ("BR-CMS-023", "modules/cms/selectors/scoping.py", "def feedback_for("),
    ("BR-CMS-024", "modules/cms/domain/rules.py", "def validate_manual_escalation("),
    ("BR-CMS-025", "modules/cms/services/escalation.py", "def escalate_manually("),
    ("BR-CMS-026", "modules/cms/domain/sla.py", "def sla_hours_for_priority("),
    ("BR-CMS-027", "modules/cms/services/policy.py", "def publish_policy("),
    ("BR-CMS-028", "modules/cms/services/sla.py", "def send_pre_breach_reminders("),
    ("BR-CMS-029", "modules/cms/services/sla.py", "def escalate_breached_complaints("),
    ("BR-CMS-030", "modules/cms/services/announcements.py", "def publish_announcement("),
    (
        "BR-CMS-031",
        "modules/cms/services/announcements.py",
        "if policy.notify_on_announcement:",
    ),
    ("BR-CMS-032", "modules/cms/selectors/reports.py", "def operational_report("),
    ("BR-CMS-033", "modules/cms/selectors/reports.py", "def analytics_summary("),
    ("BR-CMS-034", "modules/cms/models/notification.py", "class CmsNotificationEvent("),
    ("BR-CMS-035", "docs/19-cms/cms-blueprint.md", "Accepted Architectural Gap"),
    ("BR-CMS-036", "docs/19-cms/cms-blueprint.md", "Accepted Architectural Gap"),
    ("BR-CMS-037", "docs/19-cms/cms-blueprint.md", "Accepted Architectural Gap"),
    ("BR-CMS-038", "modules/cms/registry.py", "ROLE_GRANTS ="),
    ("BR-CMS-039", "modules/cms/registry.py", "MODULE ="),
    ("BR-CMS-040", "modules/cms/models/complaint.py", "class Complaint("),
    ("BR-CMS-041", "modules/cms/models/policy.py", "class CmsPolicy("),
    ("UC-CMS-001", "modules/cms/api/views.py", "class ComplaintListCreateView("),
    ("UC-CMS-002", "modules/cms/api/views.py", "class ComplaintDetailView("),
    ("UC-CMS-003", "modules/cms/selectors/scoping.py", "def complaints_for("),
    ("UC-CMS-004", "modules/cms/api/views.py", "class ComplaintHandlingSetupView("),
    ("UC-CMS-005", "modules/cms/api/views.py", "class ComplaintProgressUpdateView("),
    ("UC-CMS-006", "modules/cms/api/views.py", "class ComplaintResolveView("),
    ("UC-CMS-007", "modules/cms/api/views.py", "class ComplaintVerifyCloseView("),
    ("UC-CMS-008", "modules/cms/api/views.py", "class ReopenRequestCreateView("),
    ("UC-CMS-009", "modules/cms/api/views.py", "class FeedbackCreateView("),
    ("UC-CMS-010", "modules/cms/api/views.py", "class FeedbackListView("),
    ("UC-CMS-011", "modules/cms/api/views.py", "class ComplaintEscalateView("),
    ("UC-CMS-012", "modules/cms/selectors/scoping.py", "def complaints_for("),
    ("UC-CMS-013", "modules/cms/api/views.py", "class AnnouncementListCreateView("),
    ("UC-CMS-014", "modules/cms/selectors/scoping.py", "def announcements_for("),
    ("UC-CMS-015", "modules/cms/api/views.py", "class OperationalReportView("),
    ("UC-CMS-016", "modules/cms/api/views.py", "class EscalationSummaryView("),
    ("UC-CMS-017", "modules/cms/api/views.py", "class AnalyticsSummaryView("),
    ("UC-CMS-018", "docs/19-cms/cms-blueprint.md", "Accepted Architectural Gap"),
    ("UC-CMS-019", "modules/cms/api/views.py", "class ComplaintVerifyCloseView("),
    ("UC-CMS-020", "modules/cms/api/views.py", "class ReopenRequestDecideView("),
    ("UC-CMS-021", "modules/cms/tasks.py", "def run_pre_breach_reminders("),
    ("UC-CMS-022", "modules/cms/tasks.py", "def run_escalate_breached_complaints("),
    ("BW-CMS-01", "modules/cms/domain/state_machine.py", "TRANSITIONS:"),
    ("BW-CMS-02", "modules/cms/services/transitions.py", "def verify_and_close_complaint("),
    ("BW-CMS-03", "modules/cms/services/transitions.py", "def verify_and_close_complaint("),
    ("BW-CMS-04", "modules/cms/services/transitions.py", "def reject_complaint("),
    ("BW-CMS-05", "modules/cms/services/reopening.py", "def decide_reopening("),
    ("BW-CMS-06", "modules/cms/services/reopening.py", "req.status = ReopenRequest.DENIED"),
    ("BW-CMS-07", "modules/cms/services/escalation.py", "def escalate_manually("),
    ("BW-CMS-08", "modules/cms/services/sla.py", "def escalate_breached_complaints("),
    (
        "CW-CMS-01",
        "modules/cms/tests/test_journeys.py",
        "def test_ordinary_plain_student_lifecycle_bw_cms_01_02_cw_cms_01(",
    ),
    (
        "CW-CMS-02",
        "modules/cms/tests/test_journeys.py",
        "def test_escalation_supervisor_verification_and_reopening",
    ),
    (
        "CW-CMS-03",
        "modules/cms/tests/test_schedule.py",
        "def test_sla_reminder_and_auto_escalation_and_dispatch_are_idempotent(",
    ),
    ("CFR-CMS-001", "modules/cms/services/complaints.py", "def submit_complaint("),
    ("CFR-CMS-002", "modules/cms/services/handling.py", "def setup_complaint_handling("),
    ("CFR-CMS-003", "modules/cms/services/handling.py", "def record_progress_update("),
    ("CFR-CMS-004", "modules/cms/services/transitions.py", "def resolve_complaint("),
    ("CFR-CMS-005", "modules/cms/services/transitions.py", "def verify_and_close_complaint("),
    ("CFR-CMS-006", "modules/cms/services/reopening.py", "def request_reopening("),
    ("CFR-CMS-007", "modules/cms/services/feedback.py", "def submit_feedback("),
    ("CFR-CMS-008", "modules/cms/services/escalation.py", "def escalate_manually("),
    ("CFR-CMS-009", "modules/cms/services/sla.py", "def send_pre_breach_reminders("),
    ("CFR-CMS-010", "modules/cms/services/announcements.py", "def publish_announcement("),
    ("CFR-CMS-011", "modules/cms/selectors/reports.py", "def operational_report("),
    ("CFR-CMS-012", "modules/cms/services/notifications.py", "def enqueue_notification("),
    ("CFR-CMS-013", "docs/19-cms/cms-blueprint.md", "Accepted Architectural Gap"),
    ("CFR-CMS-014", "modules/cms/registry.py", "MODULE ="),
]


def find_line(relpath: str, needle: str) -> int:
    path = ROOT / relpath
    if not path.exists():
        raise FileNotFoundError(relpath)
    for idx, line in enumerate(path.read_text().splitlines(), start=1):
        if needle in line:
            return idx
    raise ValueError(f"Needle {needle!r} not found in {relpath}")


def main() -> int:
    lines = [
        "# Complaint Management System (`cms`) — Code Reference",
        "",
        "Generated by `ops/docs/cms_reference.py`. Every live spec ID resolves to `file:line`.",
        "",
        "| Spec ID | Enforcement Point |",
        "|---|---|",
    ]
    for spec_id, relpath, needle in MAPPINGS:
        lineno = find_line(relpath, needle)
        lines.append(f"| `{spec_id}` | `{relpath}:{lineno}` |")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT} ({len(MAPPINGS)} verified links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
