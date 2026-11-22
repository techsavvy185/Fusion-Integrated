---
title: Complaint Management System (CMS) — Architecture & Implementation Blueprint
module: cms
docs_folder: docs/19-cms/
environment: module-only
spec_source: /Users/techsavvy185/Downloads/CMS
---

# Complaint Management System (`cms`) — Blueprint

This blueprint is the Phase 2 deliverable for `modules/cms/` under `docs/19-cms/cms-blueprint.md`. No application code is written until Student 2 approves this blueprint, its accepted known gaps, and its open questions in writing.

- **Module Name:** Complaint Management System
- **Module Code / URL Segment / Permission Prefix:** `cms` (`/api/v1/cms/`, `/cms/...`, `cms.<noun>.<verb>`)
- **Docs Folder:** `docs/19-cms/` (`NN = 19`)
- **Environment:** `module-only`
- **Specification ID Prefixes:** `CFR-CMS-`, `AFR-CMS-`, `UC-CMS-`, `BR-CMS-`, `BW-CMS-`, `CW-CMS-`
- **Retired Spec IDs (Never Cited in Code or Tests):** `BR-CMS-042` (System Not Primary Actor Rule — retired as a business rule; retained only as a UC/WF modeling convention; automated SLA actions are live event-triggered use cases `UC-CMS-021` and `UC-CMS-022`).
- **RTM Status:** `06_CMS_Traceability_Matrix_v1.3_FINAL.xlsx` has 0/14 CFR and 0/73 AFR mapping columns populated; all traceability below was derived directly by reading every live CFR, AFR, UC, BR, BW, and CW document.

---

## (a) Traceability Table (Step 3.1)

Every live Business Rule (`BR-CMS-001..041`), Use Case (`UC-CMS-001..022`), Workflow (`BW-CMS-01..08`, `CW-CMS-01..03`), Composite Requirement (`CFR-CMS-001..014`), and Atomic Requirement (`AFR-CMS-001..073`) is mapped to its owning layer and planned enforcement point.

### Business Rules (`BR-CMS-001` through `BR-CMS-041`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-CMS-001 | Complaint submission available at any time to authenticated complainants | `services/` + `api/` | `services/complaints.py::submit_complaint`, `api/views.py::ComplaintListCreateView` | No time-window gate |
| BR-CMS-002 | Mandatory complaint fields (category, description, title) validated before acceptance | `domain/` + `services/` | `domain/rules.py::validate_submission`, `services/complaints.py::submit_complaint` | Rejects blank/whitespace or inactive category with 422/400 |
| BR-CMS-003 | Submission date/time recorded automatically on every accepted complaint | `models/` | `models/complaint.py::Complaint` (`TimeStampedModel.created_at`, `submitted_at`) | Server-owned, read-only in serializers |
| BR-CMS-004 | Supporting attachments validated against active policy before acceptance | `domain/` + `services/` | `domain/rules.py::validate_attachments`, `core/files/drive.py::parse` | Validates Drive URLs + configured max attachment count |
| BR-CMS-005 | Exact attachment limits are configurable policy, not hard-coded constants | `models/` + `domain/` | `models/policy.py::CmsPolicy` (`max_attachments`, `allowed_attachment_hosts`) | Effective-dated policy |
| BR-CMS-006 | Unique complaint identifier generated for each submitted complaint | `models/` + `services/` | `models/complaint.py::Complaint.tracking_code` (`UniqueConstraint`), `services/complaints.py::_next_tracking_code` | DB-enforced uniqueness |
| BR-CMS-007 | Manual assignment by Complaint Handler for operational handling | `services/` + `api/` | `services/handling.py::setup_complaint_handling` | Never auto-assigned on submission; resolves `ISS-CMS-009` |
| BR-CMS-008 | Complaint categorization by Complaint Handler using active category/type | `models/` + `services/` | `models/policy.py::ComplaintCategory`, `services/handling.py::setup_complaint_handling` | Active category required |
| BR-CMS-009 | Priority value strictly restricted to `{Low, Medium, High}` | `domain/` + `models/` | `domain/state_machine.py::PRIORITIES`, `models/complaint.py::Complaint` (`CheckConstraint`) | DB + domain enforced |
| BR-CMS-010 | Assignment and priority recorded for downstream handling, reminders, and escalation | `models/` + `services/` | `models/complaint.py::Complaint` (`assigned_to_user_id`, `assigned_unit`, `priority`, `sla_due_at`), `services/handling.py::setup_complaint_handling` | Computes `sla_due_at` from effective policy |
| BR-CMS-011 | Complaint status and chronological progress history maintained throughout lifecycle | `models/` + `services/` | `models/complaint.py::ComplaintHistory`, `services/transitions.py::transition_complaint`, `services/handling.py::record_progress_update` | Append-only history rows |
| BR-CMS-012 | Canonical complaint lifecycle state set `{submitted, in_progress, resolved, rejected, closed}` | `domain/` + `models/` | `domain/state_machine.py::STATUSES`, `models/complaint.py::Complaint` (`CheckConstraint`) | Illegal transitions inexpressible |
| BR-CMS-013 | Resolution requires non-empty resolution details | `domain/` + `services/` | `domain/state_machine.py` (`has_resolution_details` guard), `services/transitions.py::resolve_complaint` | Refuses blank details |
| BR-CMS-014 | Rejection requires non-empty rejection reason | `domain/` + `services/` | `domain/state_machine.py` (`has_rejection_reason` guard), `services/transitions.py::reject_complaint` | Refuses blank reason |
| BR-CMS-015 | Outcome and status changes trigger notification outbox records | `services/` | `services/notifications.py::enqueue_notification` called inside transactional write choke point | Triggered on submit, progress, resolve, reject, escalate, reopen, feedback, announcement |
| BR-CMS-016 | Closure verification requires Resolved state and authorized Complainant or Supervisor per policy | `domain/` + `services/` | `domain/rules.py::required_verifier`, `services/transitions.py::verify_and_close_complaint` | Resolves `ISS-CMS-010`: routine -> Complainant, escalated -> Supervisor (configurable via `CmsPolicy`) |
| BR-CMS-017 | Closure records verified_by, closed_at, and audit history | `models/` + `services/` | `models/complaint.py::Complaint` (`closed_at`, `verified_by_user_id`), `services/transitions.py::verify_and_close_complaint` | Written inside `select_for_update` transaction |
| BR-CMS-018 | Reopening request permitted only on Closed complaints by owning Complainant with dissatisfaction reason | `domain/` + `services/` | `services/reopening.py::request_reopening` | One open request per complaint enforced via partial `UniqueConstraint` |
| BR-CMS-019 | Only Complaint Supervisor may review/decide reopening requests | `api/` + `services/` | `HasPermission("cms.reopen_request.approve")`, `services/reopening.py::decide_reopening` | Handler and Complainant refused (403) |
| BR-CMS-020 | Approved reopening updates complaint status back to active handling | `domain/` + `services/` | `domain/state_machine.py` (`closed -> in_progress`), `services/reopening.py::decide_reopening` | Resolves `ISS-CMS-008`: transitions to `in_progress`, increments `reopen_count`, recomputes SLA |
| BR-CMS-021 | Reopening decision (approved/denied, reviewer, remarks, timestamp) recorded in history | `models/` + `services/` | `models/reopening.py::ReopenRequest`, `models/complaint.py::ComplaintHistory` | Immutable once decided |
| BR-CMS-022 | Feedback allowed only after complaint is Resolved or Closed, by owning Complainant | `domain/` + `services/` | `domain/rules.py::can_submit_feedback`, `services/feedback.py::submit_feedback` | One feedback per complaint (`UniqueConstraint`) |
| BR-CMS-023 | Submitted feedback readable by Complaint Handler and Complaint Supervisor (and owning Complainant) | `selectors/` | `selectors/scoping.py::feedback_for` | Non-owner complainant gets 404 |
| BR-CMS-024 | Manual escalation permitted only by Handler on unresolved, non-escalated complaints with reason | `domain/` + `services/` | `domain/rules.py::can_escalate`, `services/escalation.py::escalate_manually` | Orthogonal flag (`is_escalated=True`, `escalation_type="manual"`) |
| BR-CMS-025 | Escalation status, timestamp, type (manual/automatic), and reason tracked persistently | `models/` + `services/` | `models/complaint.py::Complaint` (`is_escalated`, `escalation_type`, `escalated_at`), `models/complaint.py::ComplaintEscalation` | Partial unique index prevents duplicate active escalations |
| BR-CMS-026 | Priority associated with active SLA timeline | `domain/` + `services/` | `domain/sla.py::compute_sla_due_at`, `services/handling.py::setup_complaint_handling` | Uses active effective-dated `CmsPolicy` |
| BR-CMS-027 | Exact SLA durations are configurable policy, never hard-coded in baseline rules | `models/` + `domain/` | `models/policy.py::CmsPolicy` (`low_sla_hours`, `medium_sla_hours`, `high_sla_hours`, `reminder_lead_hours`) | Seeded via `manage.py seed_cms_policy`; missing policy returns clear 422 remediation |
| BR-CMS-028 | Pre-breach reminder triggered once when unresolved complaint approaches SLA deadline | `services/` + `tasks.py` | `services/sla.py::send_pre_breach_reminders`, `tasks.py::send_pre_breach_reminders` | Idempotent (`reminder_sent_at` guard); non-state-changing |
| BR-CMS-029 | Unresolved complaint automatically escalated when SLA deadline is breached | `services/` + `tasks.py` | `services/sla.py::escalate_breached_complaints`, `tasks.py::escalate_breached_complaints` | Idempotent `select_for_update` + `is_escalated=False` guard |
| BR-CMS-030 | Only Complaint Handler and Complaint Supervisor may publish announcements | `api/` + `services/` | `HasPermission("cms.announcement.publish")`, `services/announcements.py::publish_announcement` | Plain complainant and admin refused (403) |
| BR-CMS-031 | Announcement notification triggered only when configured active policy enables it | `models/` + `services/` | `CmsPolicy.notify_on_announcement`, `services/announcements.py::publish_announcement` | Configurable flag |
| BR-CMS-032 | Reports, summaries, escalation summaries, and analytics scoped strictly to role permissions | `api/` + `selectors/` | `selectors/reports.py::operational_report`, `escalation_summary`, `analytics_summary` | Separate permission gates per audience |
| BR-CMS-033 | Analytics strictly limited to CMS complaint/escalation/resolution aggregates | `selectors/` | `selectors/reports.py` | No unsupported predictive/external analytics |
| BR-CMS-034 | CMS triggers notification records/outbox events; central email delivery infrastructure is external | `models/` + `services/` | `models/notification.py::CmsNotificationEvent`, `services/notifications.py::enqueue_notification` | Outbox pattern (ADR-0006); no external SMTP credentials |
| BR-CMS-035 | Time-bound CMS role assignment (`Complaint Handler`, `Complaint Supervisor`) by System Admin | **Accepted Known Gap (IAM Boundary)** | `docs/19-cms/cms-blueprint.md` §(h) | Conflicts with ADR-0002 & Step 3.4: RBAC and role assignments live exclusively in `Fusion_System_Administrator` IAM; domain modules must own no auth/role tables |
| BR-CMS-036 | Mid-cycle CMS role reassignment by System Admin | **Accepted Known Gap (IAM Boundary)** | `docs/19-cms/cms-blueprint.md` §(h) | Owned by IAM/ERP (`Fusion_System_Administrator`), not `modules/cms/` |
| BR-CMS-037 | Exactly one active Complaint Handler and one active Complaint Supervisor at a time | **Accepted Known Gap (IAM Boundary)** | `docs/19-cms/cms-blueprint.md` §(h) | Role assignment cardinality is an IAM/ERP administration responsibility per ADR-0002 |
| BR-CMS-038 | Exclude HR master-data, payroll, employment records, and platform account admin | `architecture` | `.importlinter`, no HR/auth tables in `modules/cms/models/` | Enforced structurally |
| BR-CMS-039 | Exclude payment, accounting, payroll, procurement, inventory, physical maintenance execution, platform security | `architecture` | No such models/endpoints in `modules/cms/` | Enforced structurally |
| BR-CMS-040 | External service/department complaints limited to CMS tracking/handling records | `domain/` + `models/` | `Complaint`, `ComplaintHistory` | No external dispatch/work-order engine |
| BR-CMS-041 | External institutional policies excluded unless explicitly modeled in `CmsPolicy` | `models/` + `domain/` | `models/policy.py::CmsPolicy` | No hidden hard-coded policies |

### Use Cases (`UC-CMS-001` through `UC-CMS-022`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| UC-CMS-001 | Submit Complaint (Complainant) | `api/` + `services/` | `POST /api/v1/cms/complaints/` -> `services/complaints.py::submit_complaint` | Validates fields, attachments, creates unique tracking code & notification |
| UC-CMS-002 | Track Submitted Complaint Status and History (Complainant) | `api/` + `selectors/` | `GET /api/v1/cms/complaints/`, `GET /api/v1/cms/complaints/{id}/` -> `selectors/scoping.py::complaints_for` | Strictly scoped to `user_id=actor.user_id` |
| UC-CMS-003 | Review Assigned Complaints (Handler) | `api/` + `selectors/` | `GET /api/v1/cms/complaints/` -> `selectors/scoping.py::complaints_for` | Handler sees operational worklist with filters |
| UC-CMS-004 | Assign, Categorize, and Prioritize Complaint (Handler) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/handling-setup/` -> `services/handling.py::setup_complaint_handling` | Manual assignment + category + Low/Medium/High priority + SLA due calculation |
| UC-CMS-005 | Update Complaint Progress (Handler) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/progress/` -> `services/handling.py::record_progress_update` | Appends history; transitions `submitted -> in_progress` (`ISS-CMS-007`) |
| UC-CMS-006 | Resolve or Reject Complaint (Handler) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/resolve/`, `.../reject/` -> `services/transitions.py` | Mandatory resolution details or rejection reason; triggers notification |
| UC-CMS-007 | Verify Resolved Complaint for Closure (User / Complainant) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/verify-close/` -> `services/transitions.py::verify_and_close_complaint` | Allowed when policy selects Complainant verification |
| UC-CMS-008 | Request Complaint Reopening (User / Complainant) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/reopen-requests/` -> `services/reopening.py::request_reopening` | Allowed only on own `closed` complaint with reason |
| UC-CMS-009 | Submit Feedback (User / Complainant) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/feedback/` -> `services/feedback.py::submit_feedback` | Allowed only on own `resolved` or `closed` complaint |
| UC-CMS-010 | Review Submitted Feedback (Handler / Supervisor) | `api/` + `selectors/` | `GET /api/v1/cms/feedback/` -> `selectors/scoping.py::feedback_for` | Paginated feedback review list |
| UC-CMS-011 | Manually Escalate Unresolved Complaint (Handler) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/escalate/` -> `services/escalation.py::escalate_manually` | Sets `is_escalated=True`, `escalation_type="manual"`, records reason & notification |
| UC-CMS-012 | Monitor Escalated Complaints (Supervisor) | `api/` + `selectors/` | `GET /api/v1/cms/complaints/?escalated=true` -> `selectors/scoping.py::complaints_for` | Supervisor oversight view of escalated complaints |
| UC-CMS-013 | Publish Complaint-Related Announcement (Handler / Supervisor) | `api/` + `services/` | `POST /api/v1/cms/announcements/` -> `services/announcements.py::publish_announcement` | Triggers notification event when policy enables it |
| UC-CMS-014 | View Complaint-Related Announcements (Complainant) | `api/` + `selectors/` | `GET /api/v1/cms/announcements/` -> `selectors/scoping.py::announcements_for` | Active published announcements visible to complainants |
| UC-CMS-015 | Generate Operational Complaint Reports (Handler) | `api/` + `selectors/` | `GET /api/v1/cms/reports/operational/` -> `selectors/reports.py::operational_report` | Counts by status, category, priority, overdue |
| UC-CMS-016 | View Complaint and Escalation Summaries (Supervisor) | `api/` + `selectors/` | `GET /api/v1/cms/reports/escalations/` -> `selectors/reports.py::escalation_summary` | Escalation breakdown (manual vs automatic) + complaint summaries |
| UC-CMS-017 | View CMS Reports and Analytics (System Admin) | `api/` + `selectors/` | `GET /api/v1/cms/reports/analytics/` -> `selectors/reports.py::analytics_summary` | Overall CMS volume, turnaround, escalation, and feedback metrics |
| UC-CMS-018 | Manage CMS Roles (System Admin) | **Accepted Known Gap (IAM Boundary)** | `docs/19-cms/cms-blueprint.md` §(h) | Deferred to `Fusion_System_Administrator` IAM per ADR-0002 & Step 3.4 |
| UC-CMS-019 | Verify Resolved Complaint for Closure (Complaint Supervisor) | `api/` + `services/` | `POST /api/v1/cms/complaints/{id}/verify-close/` -> `services/transitions.py::verify_and_close_complaint` | Allowed when policy selects Supervisor verification (e.g. escalated complaints) |
| UC-CMS-020 | Review Complaint Reopening Request (Complaint Supervisor) | `api/` + `services/` | `POST /api/v1/cms/reopen-requests/{id}/decide/` -> `services/reopening.py::decide_reopening` | Approve -> `in_progress`, Deny -> stays `closed`; triggers notification |
| UC-CMS-021 | Trigger Pre-Breach SLA Reminder (Event-triggered) | `services/` + `tasks.py` | `tasks.py::send_pre_breach_reminders` -> `services/sla.py::send_pre_breach_reminders` | Scheduled Celery Beat task; idempotent |
| UC-CMS-022 | Automatically Escalate Complaint on SLA Breach (Event-triggered) | `services/` + `tasks.py` | `tasks.py::escalate_breached_complaints` -> `services/sla.py::escalate_breached_complaints` | Scheduled Celery Beat task; idempotent |

### Workflows (`BW-CMS-01..08`, `CW-CMS-01..03`) & Requirements (`CFR-CMS-001..014`, `AFR-CMS-001..073`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BW-CMS-01 | Submit -> Setup -> Progress (0/1) -> Resolve (no closure yet) | `domain/` + `services/` | `domain/state_machine.py::TRANSITIONS`, `services/transitions.py` | Verified by `test_journeys.py` & `test_state_machine.py` |
| BW-CMS-02 | Submit -> Setup -> Progress -> Resolve -> Complainant Verification -> Closed | `domain/` + `services/` | `services/transitions.py::verify_and_close_complaint` | Routine complaint path |
| BW-CMS-03 | Submit -> Setup -> Progress -> Resolve -> Supervisor Verification -> Closed | `domain/` + `services/` | `services/transitions.py::verify_and_close_complaint` | Escalated / supervisor-verified path |
| BW-CMS-04 | Submit -> Setup -> Progress -> Reject -> Rejected | `domain/` + `services/` | `services/transitions.py::reject_complaint` | Terminal rejected path |
| BW-CMS-05 | Closed -> Reopen Request -> Supervisor Approves -> Active (`in_progress`) | `domain/` + `services/` | `services/reopening.py::request_reopening`, `decide_reopening` | Approved reopening path |
| BW-CMS-06 | Closed -> Reopen Request -> Supervisor Denies -> Remains Closed | `domain/` + `services/` | `services/reopening.py::decide_reopening` | Denied reopening path |
| BW-CMS-07 | Active Unresolved -> Manual Escalation -> Escalated (manual) | `domain/` + `services/` | `services/escalation.py::escalate_manually` | Orthogonal escalation flag |
| BW-CMS-08 | Active Unresolved + SLA Breached -> Automatic Escalation -> Escalated (automatic) | `services/` + `tasks.py` | `services/sla.py::escalate_breached_complaints` | System actor transition |
| CW-CMS-01 | End-to-End Complaint Lifecycle (BW-CMS-01..04) | `domain/` + `services/` | `services/complaints.py`, `handling.py`, `transitions.py` | Covered end-to-end in HTTP journey tests |
| CW-CMS-02 | Complaint Reopening Decision (BW-CMS-05..06) | `domain/` + `services/` | `services/reopening.py` | Covered end-to-end in HTTP journey tests |
| CW-CMS-03 | Complaint Escalation Paths (BW-CMS-07..08) | `services/` + `tasks.py` | `services/escalation.py`, `services/sla.py` | Covered in escalation + schedule tests |
| CFR-CMS-001 / AFR-CMS-001..010 | Complaint Submission, Validation, Attachments, Unique ID, Confirmation | `domain/` + `models/` + `services/` | `services/complaints.py::submit_complaint`, `domain/rules.py` | All 10 AFRs enforced |
| CFR-CMS-002 / AFR-CMS-011..015 | Manual Assignment, Categorization, Priority, Downstream Recording | `models/` + `services/` | `services/handling.py::setup_complaint_handling` | All 5 AFRs enforced |
| CFR-CMS-003 / AFR-CMS-016..021 | Complainant Tracking, Handler Review/Updates, Status & Progress History | `models/` + `selectors/` + `services/` | `selectors/scoping.py`, `services/handling.py::record_progress_update` | All 6 AFRs enforced |
| CFR-CMS-004 / AFR-CMS-022..026 | Lifecycle States, Resolution/Rejection Details, Outcome Notifications | `domain/` + `services/` | `domain/state_machine.py`, `services/transitions.py` | All 5 AFRs enforced |
| CFR-CMS-005 / AFR-CMS-027..029 | Complainant & Supervisor Closure Verification and Closure Recording | `domain/` + `services/` | `services/transitions.py::verify_and_close_complaint` | All 3 AFRs enforced |
| CFR-CMS-006 / AFR-CMS-030..034 | Reopening Request, Supervisor Review, Status Update, Outcome Recording | `models/` + `services/` | `services/reopening.py` | All 5 AFRs enforced |
| CFR-CMS-007 / AFR-CMS-035..037 | Post-Resolution/Closure Feedback Submission & Handler/Supervisor Review | `models/` + `services/` + `selectors/` | `services/feedback.py`, `selectors/scoping.py::feedback_for` | All 3 AFRs enforced |
| CFR-CMS-008 / AFR-CMS-038..040 | Manual Escalation, Escalation Status Tracking, Supervisor Monitoring | `models/` + `services/` + `selectors/` | `services/escalation.py`, `selectors/scoping.py` | All 3 AFRs enforced |
| CFR-CMS-009 / AFR-CMS-041..044 | Priority-SLA Association, Configurable Durations, Pre-Breach Reminder, Auto-Escalation | `models/` + `domain/` + `services/` + `tasks.py` | `models/policy.py`, `domain/sla.py`, `services/sla.py` | All 4 AFRs enforced |
| CFR-CMS-010 / AFR-CMS-045..048 | Announcement Publishing (Handler/Supervisor), Viewing (Complainant), Configured Notification | `models/` + `services/` + `selectors/` | `services/announcements.py`, `selectors/scoping.py` | All 4 AFRs enforced |
| CFR-CMS-011 / AFR-CMS-049..054 | Role-Scoped Reports, Summaries, Escalation Summaries, Analytics | `selectors/` + `api/` | `selectors/reports.py` | All 6 AFRs enforced |
| CFR-CMS-012 / AFR-CMS-055..063 | Notification Triggering for all 8 Events & Outbox Scope Boundary | `models/` + `services/` | `models/notification.py::CmsNotificationEvent`, `services/notifications.py` | All 9 AFRs enforced |
| CFR-CMS-013 / AFR-CMS-064..070 | Time-bound CMS Role Assignment, Reassignment, Cardinality, Scope Boundary | **Accepted Known Gap** (`AFR-CMS-064..068`); Structural (`AFR-CMS-069..070`) | `docs/19-cms/cms-blueprint.md` §(h) | `AFR-CMS-064..068` delegated to IAM per ADR-0002; `AFR-CMS-069..070` structurally satisfied |
| CFR-CMS-014 / AFR-CMS-071..073 | Cross-module, External Service, and External Policy Boundaries | `architecture` | `.importlinter`, module boundary design | All 3 AFRs enforced |

---

## (b) Domain Model (Step 3.2)

All models live as a package under `modules/cms/models/` (one file per aggregate), inheriting `TimeStampedModel` / `UserScopedModel` from `core.db.mixins`. Every person reference is a plain integer `user_id` (no cross-module or cross-DB FKs).

1. **`modules/cms/models/policy.py`**
   - **`ComplaintCategory(TimeStampedModel)`**:
     - `code` (`CharField(max_length=40)`, unique), `name` (`CharField(max_length=120)`), `description` (`TextField(blank=True)`), `is_active` (`BooleanField(default=True)`).
     - Constraint: `UniqueConstraint(fields=["code"], name="cms_category_code_uniq")`.
     - Index: `Index(fields=["is_active", "name"], name="cms_category_active_name_idx")`.
   - **`CmsPolicy(TimeStampedModel)`** (effective-dated, never mutated in place — superseded by creating a newer effective version):
     - `version` (`PositiveIntegerField`), `effective_from` (`DateTimeField`), `is_active` (`BooleanField(default=True)`).
     - `low_sla_hours` (`PositiveIntegerField`), `medium_sla_hours` (`PositiveIntegerField`), `high_sla_hours` (`PositiveIntegerField`).
     - `reminder_lead_hours` (`PositiveIntegerField`).
     - `max_attachments` (`PositiveSmallIntegerField(default=5)`).
     - `routine_verification_by` (`CharField(max_length=20)` — `complainant` | `supervisor` | `either`, default `complainant`).
     - `escalated_verification_by` (`CharField(max_length=20)` — `complainant` | `supervisor` | `either`, default `supervisor`).
     - `notify_on_announcement` (`BooleanField(default=True)`).
     - `created_by_user_id` (`IntegerField`).
     - Constraints:
       - `UniqueConstraint(fields=["version"], name="cms_policy_version_uniq")`
       - `UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="cms_policy_single_active_uniq")`
       - `CheckConstraint(check=Q(low_sla_hours__gt=0, medium_sla_hours__gt=0, high_sla_hours__gt=0, reminder_lead_hours__gt=0), name="cms_policy_positive_hours_chk")`
       - `CheckConstraint(check=Q(reminder_lead_hours__lt=F("high_sla_hours")), name="cms_policy_reminder_lt_high_sla_chk")`
     - Index: `Index(fields=["is_active", "-effective_from"], name="cms_policy_active_eff_idx")`.

2. **`modules/cms/models/complaint.py`**
   - **`Complaint(TimeStampedModel, UserScopedModel)`**:
     - `tracking_code` (`CharField(max_length=32)`), `category` (`ForeignKey(ComplaintCategory, on_delete=PROTECT)`).
     - `title` (`CharField(max_length=200)`), `description` (`TextField`).
     - `status` (`CharField(max_length=20)`, default `"submitted"` — choices: `submitted`, `in_progress`, `resolved`, `rejected`, `closed`).
     - `priority` (`CharField(max_length=16)`, blank=True, default `""` — choices: `""`, `Low`, `Medium`, `High`).
     - `assigned_to_user_id` (`IntegerField(null=True, blank=True, db_index=True)`), `assigned_unit` (`CharField(max_length=120, blank=True, default="")`), `assigned_by_user_id` (`IntegerField(null=True, blank=True)`), `assigned_at` (`DateTimeField(null=True, blank=True)`).
     - `policy` (`ForeignKey(CmsPolicy, on_delete=PROTECT)` — pinned at submission/priority assignment).
     - `sla_due_at` (`DateTimeField(null=True, blank=True)`), `reminder_sent_at` (`DateTimeField(null=True, blank=True)`).
     - `is_escalated` (`BooleanField(default=False)`), `escalation_type` (`CharField(max_length=16, blank=True, default="")` — `""`, `manual`, `automatic`), `escalated_at` (`DateTimeField(null=True, blank=True)`), `escalation_reason` (`TextField(blank=True, default="")`).
     - `resolution_details` (`TextField(blank=True, default="")`), `resolved_at` (`DateTimeField(null=True, blank=True)`), `resolved_by_user_id` (`IntegerField(null=True, blank=True)`).
     - `rejection_reason` (`TextField(blank=True, default="")`), `rejected_at` (`DateTimeField(null=True, blank=True)`), `rejected_by_user_id` (`IntegerField(null=True, blank=True)`).
     - `closed_at` (`DateTimeField(null=True, blank=True)`), `verified_by_user_id` (`IntegerField(null=True, blank=True)`), `verified_by_role` (`CharField(max_length=32, blank=True, default="")`).
     - `reopen_count` (`PositiveIntegerField(default=0)`), `last_reopened_at` (`DateTimeField(null=True, blank=True)`).
     - Constraints:
       - `UniqueConstraint(fields=["tracking_code"], name="cms_complaint_tracking_code_uniq")`
       - `CheckConstraint(check=Q(status__in=["submitted", "in_progress", "resolved", "rejected", "closed"]), name="cms_complaint_status_valid_chk")`
       - `CheckConstraint(check=Q(priority__in=["", "Low", "Medium", "High"]), name="cms_complaint_priority_valid_chk")`
       - `CheckConstraint(check=Q(escalation_type__in=["", "manual", "automatic"]), name="cms_complaint_esc_type_valid_chk")`
     - Indexes:
       - `Index(fields=["user_id", "-created_at"], name="cms_complaint_user_created_idx")`
       - `Index(fields=["status", "-created_at"], name="cms_complaint_status_created_idx")`
       - `Index(fields=["is_escalated", "status", "-created_at"], name="cms_complaint_esc_status_idx")`
       - `Index(fields=["sla_due_at", "status", "is_escalated"], name="cms_complaint_sla_sweep_idx")`
   - **`ComplaintAttachment(TimeStampedModel)`**:
     - `complaint` (`ForeignKey(Complaint, on_delete=CASCADE, related_name="attachments")`), `uploaded_by_user_id` (`IntegerField`), `label` (`CharField(max_length=120)`), `drive_file_id` (`CharField(max_length=200)`), `url` (`URLField(max_length=500)`).
     - Index: `Index(fields=["complaint", "created_at"], name="cms_attach_complaint_idx")`.
   - **`ComplaintHistory(TimeStampedModel)`** (append-only audit & progress log):
     - `complaint` (`ForeignKey(Complaint, on_delete=CASCADE, related_name="history")`), `actor_user_id` (`IntegerField(null=True, blank=True)` — `None` for System SLA tasks), `actor_role` (`CharField(max_length=64)`), `event_type` (`CharField(max_length=40)`), `from_status` (`CharField(max_length=20, blank=True, default="")`), `to_status` (`CharField(max_length=20, blank=True, default="")`), `note` (`TextField(blank=True, default="")`).
     - Index: `Index(fields=["complaint", "created_at"], name="cms_history_complaint_idx")`.

3. **`modules/cms/models/reopening.py`**
   - **`ReopenRequest(TimeStampedModel)`**:
     - `complaint` (`ForeignKey(Complaint, on_delete=CASCADE, related_name="reopen_requests")`), `requested_by_user_id` (`IntegerField`), `reason` (`TextField`), `status` (`CharField(max_length=16, default="pending")` — `pending`, `approved`, `denied`), `decided_by_user_id` (`IntegerField(null=True, blank=True)`), `decision_note` (`TextField(blank=True, default="")`), `decided_at` (`DateTimeField(null=True, blank=True)`).
     - Constraints:
       - `UniqueConstraint(fields=["complaint"], condition=Q(status="pending"), name="cms_reopen_single_pending_uniq")`
       - `CheckConstraint(check=Q(status__in=["pending", "approved", "denied"]), name="cms_reopen_status_valid_chk")`
     - Index: `Index(fields=["status", "-created_at"], name="cms_reopen_status_created_idx")`.

4. **`modules/cms/models/feedback.py`**
   - **`ComplaintFeedback(TimeStampedModel)`**:
     - `complaint` (`ForeignKey(Complaint, on_delete=CASCADE, related_name="feedback_entries")`), `submitted_by_user_id` (`IntegerField`), `rating` (`PositiveSmallIntegerField`), `comment` (`TextField(blank=True, default="")`).
     - Constraints:
       - `UniqueConstraint(fields=["complaint"], name="cms_feedback_one_per_complaint_uniq")`
       - `CheckConstraint(check=Q(rating__gte=1, rating__lte=5), name="cms_feedback_rating_range_chk")`
     - Index: `Index(fields=["-created_at"], name="cms_feedback_created_idx")`.

5. **`modules/cms/models/announcement.py`**
   - **`ComplaintAnnouncement(TimeStampedModel)`**:
     - `title` (`CharField(max_length=200)`), `body` (`TextField`), `published_by_user_id` (`IntegerField`), `published_by_role` (`CharField(max_length=64)`), `published_at` (`DateTimeField`), `is_active` (`BooleanField(default=True)`).
     - Index: `Index(fields=["is_active", "-published_at"], name="cms_announce_active_pub_idx")`.

6. **`modules/cms/models/notification.py`**
   - **`CmsNotificationEvent(TimeStampedModel)`** (outbox record per `BR-CMS-034` & ADR-0006):
     - `complaint` (`ForeignKey(Complaint, on_delete=CASCADE, null=True, blank=True, related_name="notification_events")`), `announcement` (`ForeignKey(ComplaintAnnouncement, on_delete=CASCADE, null=True, blank=True, related_name="notification_events")`), `recipient_user_id` (`IntegerField(null=True, blank=True, db_index=True)` — `None` for broadcast announcements), `event_type` (`CharField(max_length=48)`), `subject` (`CharField(max_length=200)`), `message` (`TextField`), `dedupe_key` (`CharField(max_length=120, unique=True)`), `dispatched_at` (`DateTimeField(null=True, blank=True)`).
     - Index: `Index(fields=["dispatched_at", "created_at"], name="cms_notif_dispatch_idx")`.

---

## (c) State Machine (Step 3.3)

Implemented in `modules/cms/domain/state_machine.py` as a pure-Python declarative tuple of `Transition(frm, to, permission, actors, guards)` — zero Django imports, zero `if/elif` status chains.

**Canonical States (`BR-CMS-012`):** `submitted`, `in_progress`, `resolved`, `rejected`, `closed`.
- **Terminal State:** `rejected` (cannot leave `rejected`).
- **`closed`** can only leave via Supervisor-approved reopening (`closed -> in_progress`).
- **Orthogonal Flag (`CW-CMS-03`, `BR-CMS-024`, `BR-CMS-025`):** `is_escalated` (`False -> True` via `manual` by Handler or `automatic` by System on `submitted` / `in_progress`).

| From State | To State | Permission Code | Allowed Actors | Guards | Spec IDs |
|---|---|---|---|---|---|
| `submitted` | `in_progress` | `cms.complaint.update` | `handler` | `has_handling_setup` | `UC-CMS-005`, `BR-CMS-011`, `ISS-CMS-007` |
| `in_progress` | `in_progress` | `cms.complaint.update` | `handler` | `has_progress_note` | `UC-CMS-005`, `BR-CMS-011` |
| `submitted` | `resolved` | `cms.complaint.update` | `handler` | `has_handling_setup`, `has_resolution_details` | `UC-CMS-006`, `BR-CMS-013`, `BW-CMS-01` |
| `in_progress` | `resolved` | `cms.complaint.update` | `handler` | `has_resolution_details` | `UC-CMS-006`, `BR-CMS-013`, `BW-CMS-01` |
| `submitted` | `rejected` | `cms.complaint.update` | `handler` | `has_rejection_reason` | `UC-CMS-006`, `BR-CMS-014`, `BW-CMS-04` |
| `in_progress` | `rejected` | `cms.complaint.update` | `handler` | `has_rejection_reason` | `UC-CMS-006`, `BR-CMS-014`, `BW-CMS-04` |
| `resolved` | `closed` | `cms.complaint.approve` | `complainant`, `supervisor` | `matches_required_verifier` | `UC-CMS-007`, `UC-CMS-019`, `BR-CMS-016`, `BW-CMS-02`, `BW-CMS-03` |
| `closed` | `in_progress` | `cms.reopen_request.approve` | `supervisor` | `has_pending_reopen_request` | `UC-CMS-020`, `BR-CMS-019`, `BR-CMS-020`, `BW-CMS-05` |

All writes go through one transactional choke point (`services/transitions.py`) using `Complaint.objects.select_for_update()`.

---

## (d) Permission List & `registry.py` (Step 3.4)

All permission codes strictly follow `<module_code>.<singular_noun>.<verb>` using **only** the closed verb vocabulary from `docs/02-iam/rbac-model.md` (`view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`).

```python
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
    {"code": "cms.complaints", "label": "Complaints", "icon": "ClipboardText",
     "to": "/cms/complaints", "required_permission": "cms.complaint.view", "sort_order": 10},
    {"code": "cms.escalations", "label": "Escalations", "icon": "Warning",
     "to": "/cms/escalations", "required_permission": "cms.escalation.view", "sort_order": 20},
    {"code": "cms.reopen_requests", "label": "Reopen Requests", "icon": "ArrowCounterClockwise",
     "to": "/cms/reopen-requests", "required_permission": "cms.reopen_request.approve", "sort_order": 30},
    {"code": "cms.feedback", "label": "Feedback", "icon": "Star",
     "to": "/cms/feedback", "required_permission": "cms.feedback.review", "sort_order": 40},
    {"code": "cms.announcements", "label": "Announcements", "icon": "Megaphone",
     "to": "/cms/announcements", "required_permission": "cms.announcement.view", "sort_order": 50},
    {"code": "cms.reports", "label": "Reports & Analytics", "icon": "ChartBar",
     "to": "/cms/reports", "required_permission": "cms.report.view", "sort_order": 60},
    {"code": "cms.policy", "label": "CMS Policy", "icon": "SlidersHorizontal",
     "to": "/cms/policy", "required_permission": "cms.policy.manage", "sort_order": 70},
]

PERMISSIONS = [
    ("cms.complaint.view", "View complaints within the caller's role scope"),
    ("cms.complaint.create", "Submit a new complaint"),
    ("cms.complaint.assign", "Manually assign, categorize, and prioritize a complaint"),
    ("cms.complaint.update", "Update complaint progress, resolve, reject, or escalate a complaint"),
    ("cms.complaint.approve", "Verify a resolved complaint for closure"),
    ("cms.reopen_request.create", "Request reopening of a closed complaint"),
    ("cms.reopen_request.approve", "Review and approve or deny complaint reopening requests"),
    ("cms.feedback.create", "Submit feedback on a resolved or closed complaint"),
    ("cms.feedback.review", "Review submitted complaint feedback"),
    ("cms.escalation.view", "Monitor escalated complaints"),
    ("cms.announcement.view", "View complaint-related announcements"),
    ("cms.announcement.publish", "Publish complaint-related announcements"),
    ("cms.report.view", "View role-appropriate complaint reports, summaries, and analytics"),
    ("cms.policy.manage", "Manage complaint categories and effective-dated SLA/attachment policy"),
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
```

- **Role Derivation Citations (Step 2.4):**
  - `student`, `faculty`, `staff` -> User / Complainant (`UC-CMS-001`, `002`, `007`, `008`, `009`, `014`).
  - `Complaint Handler` -> Complaint Handler (`UC-CMS-003..006`, `010`, `011`, `013`, `015`). Not yet in `globals_designation`; listed in §(h) for ERP creation in production and provisioned in dev via IAM for testing.
  - `Complaint Supervisor` -> Complaint Supervisor (`UC-CMS-010`, `012`, `013`, `016`, `019`, `020`). Not yet in `globals_designation`; listed in §(h) for ERP creation in production and provisioned in dev via IAM for testing.
  - `adminstrator` (exact spelling from `globals_designation` row id=60) -> System Admin (`UC-CMS-017`, `BR-CMS-032`, `BR-CMS-033`, policy configuration).

---

## (e) Endpoint List, Client Routes & `Fusion-client` Sidebar Entry (Step 3.5)

Every endpoint sits behind `[HasModuleGrant("cms"), HasPermission(...)]` (two gates), validates query params (400 on bad params, never 500), and carries a `throttle_scope` on every write (`cms_write`: `60/min`).

### API Endpoints (`/api/v1/cms/`)

| Method | Path | Gates (`HasModuleGrant("cms")` + Permission) | Returns | Rule / UC IDs |
|---|---|---|---|---|
| `GET` | `/api/v1/cms/categories/` | `cms.complaint.view` or `cms.policy.manage` | Active categories list | `BR-CMS-002`, `BR-CMS-008` |
| `POST` | `/api/v1/cms/categories/` | `cms.policy.manage` | Created `ComplaintCategory` (201) | `BR-CMS-008` |
| `GET` | `/api/v1/cms/policy/` | `cms.policy.manage` | Effective-dated policy history & active version | `BR-CMS-005`, `BR-CMS-027`, `BR-CMS-031` |
| `POST` | `/api/v1/cms/policy/` | `cms.policy.manage` | New effective-dated `CmsPolicy` version (201) | `BR-CMS-005`, `BR-CMS-027`, `BR-CMS-031` |
| `GET` | `/api/v1/cms/complaints/` | `cms.complaint.view` | Paginated role-scoped complaints (`?status=`, `?priority=`, `?escalated=`, `?category=`, `?search=`) | `UC-CMS-002`, `UC-CMS-003`, `UC-CMS-012` |
| `POST` | `/api/v1/cms/complaints/` | `cms.complaint.create` | Created complaint with tracking code & attachments (201) | `UC-CMS-001`, `BR-CMS-001..006` |
| `GET` | `/api/v1/cms/complaints/{id}/` | `cms.complaint.view` | Complaint detail + attachments + full history + feedback + reopen requests (404 out of scope) | `UC-CMS-002`, `UC-CMS-003`, `BR-CMS-011` |
| `POST` | `/api/v1/cms/complaints/{id}/handling-setup/` | `cms.complaint.assign` | Updated complaint with manual assignment, category, priority, `sla_due_at` | `UC-CMS-004`, `BR-CMS-007..010`, `BR-CMS-026` |
| `POST` | `/api/v1/cms/complaints/{id}/progress/` | `cms.complaint.update` | Updated complaint + appended history row | `UC-CMS-005`, `BR-CMS-011`, `BR-CMS-015` |
| `POST` | `/api/v1/cms/complaints/{id}/resolve/` | `cms.complaint.update` | Resolved complaint | `UC-CMS-006`, `BR-CMS-012`, `BR-CMS-013`, `BR-CMS-015` |
| `POST` | `/api/v1/cms/complaints/{id}/reject/` | `cms.complaint.update` | Rejected complaint | `UC-CMS-006`, `BR-CMS-012`, `BR-CMS-014`, `BR-CMS-015` |
| `POST` | `/api/v1/cms/complaints/{id}/verify-close/` | `cms.complaint.approve` | Closed complaint | `UC-CMS-007`, `UC-CMS-019`, `BR-CMS-016`, `BR-CMS-017` |
| `POST` | `/api/v1/cms/complaints/{id}/escalate/` | `cms.complaint.update` | Manually escalated complaint | `UC-CMS-011`, `BR-CMS-024`, `BR-CMS-025`, `BW-CMS-07` |
| `POST` | `/api/v1/cms/complaints/{id}/reopen-requests/` | `cms.reopen_request.create` | Created pending `ReopenRequest` (201) | `UC-CMS-008`, `BR-CMS-018` |
| `GET` | `/api/v1/cms/reopen-requests/` | `cms.reopen_request.approve` | Paginated reopen requests (`?status=`) | `UC-CMS-020`, `BR-CMS-019` |
| `POST` | `/api/v1/cms/reopen-requests/{id}/decide/` | `cms.reopen_request.approve` | Decided `ReopenRequest` + updated complaint | `UC-CMS-020`, `BR-CMS-019..021`, `BW-CMS-05`, `BW-CMS-06` |
| `POST` | `/api/v1/cms/complaints/{id}/feedback/` | `cms.feedback.create` | Created `ComplaintFeedback` (201) | `UC-CMS-009`, `BR-CMS-022` |
| `GET` | `/api/v1/cms/feedback/` | `cms.feedback.review` | Paginated feedback list | `UC-CMS-010`, `BR-CMS-023` |
| `GET` | `/api/v1/cms/announcements/` | `cms.announcement.view` | Paginated published announcements | `UC-CMS-014`, `CFR-CMS-010` |
| `POST` | `/api/v1/cms/announcements/` | `cms.announcement.publish` | Published `ComplaintAnnouncement` (201) | `UC-CMS-013`, `BR-CMS-030`, `BR-CMS-031` |
| `GET` | `/api/v1/cms/reports/operational/` | `cms.report.view` + Handler scope | Operational report for Handler | `UC-CMS-015`, `BR-CMS-032` |
| `GET` | `/api/v1/cms/reports/escalations/` | `cms.report.view` + `cms.escalation.view` | Complaint & escalation summary for Supervisor | `UC-CMS-016`, `BR-CMS-032` |
| `GET` | `/api/v1/cms/reports/analytics/` | `cms.report.view` + `cms.policy.manage` | CMS reports & analytics for System Admin | `UC-CMS-017`, `BR-CMS-032`, `BR-CMS-033` |

### Client Routes & Route Guards (`client/src/modules/cms/routes.tsx`)
Every route matches its `NAV_ITEMS` entry 1-to-1 (details open in drawers/modals on the list page, never separate routes):
- `/cms/complaints` — Open to roles holding `cms.complaint.view` (`RequirePermission("cms.complaint.view")`); action buttons gated per-control with `can(...)` (submit, handling setup, progress, resolve/reject, verify-close, escalate, reopen request, feedback).
- `/cms/escalations` — Guarded with `RequirePermission("cms.escalation.view")` (Supervisor only).
- `/cms/reopen-requests` — Guarded with `RequirePermission("cms.reopen_request.approve")` (Supervisor only).
- `/cms/feedback` — Guarded with `RequirePermission("cms.feedback.review")` (Handler & Supervisor).
- `/cms/announcements` — Guarded with `RequirePermission("cms.announcement.view")`; publish form gated with `can("cms.announcement.publish")`.
- `/cms/reports` — Guarded with `RequirePermission("cms.report.view")`; tabs gated by role capability (Operational for Handler, Escalation Summary for Supervisor, Analytics for System Admin).
- `/cms/policy` — Guarded with `RequirePermission("cms.policy.manage")` (System Admin only).

### `Fusion-client` Sidebar Entry (for `INTEGRATED_MODULES` in `Fusion-client/src/ui/nav/navigation.js`)
Because this is a `module-only` environment without `Fusion-client`, this exact entry is provided for handover:
```js
{
  id: "cms",
  label: "Complaints",
  icon: "WarningCircle",
  to: "/cms/complaints",
  section: "Services",
}
```

---

## (f) Contracts (Step 3.6)

- **Exposed by `modules/cms/contracts.py` (plural getters only):**
  - `get_complaint_summaries(user_ids: Sequence[int]) -> dict[int, ComplaintSummaryDTO]` — returns `{user_id: ComplaintSummaryDTO(user_id, total, open_count, resolved_count, escalated_count)}`.
- **Consumed from other modules / IAM:**
  - `modules.directory.contracts.get_users(user_ids)` / `search_users(...)` (via IAM projection) to display names for complainants/assignees and validate optional `assigned_to_user_id` on manual assignment without ever querying `auth_user` or `fusionlab`. Gracefully handles sparse/empty fixture results in `module-only`.
  - No new `IamClient` endpoints are required.

---

## (g) Scheduled Work (Step 3.7)

Exported in `modules/cms/schedule.py` (`BEAT_SCHEDULE`, `TASK_ROUTES`) and merged into `config/celery.py`:

| Beat Entry | Task Name | Cadence | Queue | What breaks if it does not run |
|---|---|---|---|---|
| `cms.send-pre-breach-reminders` | `cms.send_pre_breach_reminders` | Every `300s` (`expires: 290`) | `notifications` | Approaching-SLA unresolved complaints never trigger pre-breach reminder notifications (`UC-CMS-021`, `BR-CMS-028`) |
| `cms.escalate-breached-complaints` | `cms.escalate_breached_complaints` | Every `300s` (`expires: 290`) | `default` | Overdue unresolved complaints stay unescalated past SLA breach (`UC-CMS-022`, `BR-CMS-029`, `BW-CMS-08`) |
| `cms.dispatch-notifications` | `cms.dispatch_notifications` | Every `60s` (`expires: 55`) | `notifications` | Queued outbox `CmsNotificationEvent` records remain undispatched (`BR-CMS-034`, ADR-0006) |

Every task is strictly idempotent (`select_for_update` + timestamp/flag guards + unique `dedupe_key`) so running twice sequentially or concurrently takes effect exactly once.

---

## (h) Open Questions, Accepted Gaps & Pre-Implementation Approvals (Step 3.8)

1. **Accepted Architectural Gap — CMS Role Management (`CFR-CMS-013`, `AFR-CMS-064..068`, `UC-CMS-018`, `BR-CMS-035`, `BR-CMS-036`, `BR-CMS-037`):**
   - **Reason:** Fusion ADR-0002 and `new-module-prompt.md` Step 3.4 strictly forbid domain modules from owning `Role`, `Permission`, `UserRole`, or `ModuleAccess` tables or writing to `fusionlab` / `fusion_system_db`. Role assignment, duration, reassignment, and cardinality belong exclusively to `Fusion_System_Administrator` (IAM/ERP). `AFR-CMS-069` and `AFR-CMS-070` (no HR/platform account admin inside CMS) remain structurally satisfied.
2. **New Designations Needed in Production ERP (`Complaint Handler`, `Complaint Supervisor`):**
   - Neither designation exists in the 112 rows of `globals_designation` in `fusion-dev.dump`. For production deployment, the academic/admin office must create `"Complaint Handler"` and `"Complaint Supervisor"` in `globals_designation`. For local dev and E2E testing, we will provision them via IAM against synthetic test accounts.
3. **Resolved Spec Clarifications (`ISS-CMS-007` through `ISS-CMS-010`) — Proposed Design Decisions:**
   - `ISS-CMS-007`: Handling setup (`UC-CMS-004`) records category/priority/assignment on `submitted`; first progress update (`UC-CMS-005`) transitions `submitted -> in_progress`.
   - `ISS-CMS-008`: Supervisor approval of a reopening request (`UC-CMS-020`) transitions `closed -> in_progress`, increments `reopen_count`, and recomputes `sla_due_at`.
   - `ISS-CMS-009`: Manual assignment (`UC-CMS-004`) stores optional `assigned_to_user_id` and/or `assigned_unit` text; never auto-assigned on submission.
   - `ISS-CMS-010`: Effective-dated `CmsPolicy` governs closure verification (`routine_verification_by="complainant"`, `escalated_verification_by="supervisor"`), allowing both `UC-CMS-007` and `UC-CMS-019` to be enforced deterministically.
4. **No Unseeded Policy 500s (`Step 2.8`):**
   - If `CmsPolicy` has not been seeded yet, `readiness()` reports `"No active CMS policy exists — run 'manage.py seed_cms_policy'"` and write endpoints requiring SLA/policy return HTTP `422` (`code="cms_policy_not_configured"`) with clear remediation rather than `500`.
5. **Pre-approved Shared-File Registrations (`Step 4.0`):**
   - Only the pre-approved registration lines (`config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, `client/e2e/accounts.ts`, `ops/docs/cms_reference.py`, and regenerated schema/permission files) will be touched outside `modules/cms/`, `client/src/modules/cms/`, `client/e2e/cms/`, and `docs/19-cms/`. No new Python or npm dependencies are needed.
