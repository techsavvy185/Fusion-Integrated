# CMS Domain Model, State Machine & Deployment Order

## Domain Model
- `ComplaintCategory`: Active complaint types (`code` unique).
- `CmsPolicy`: Effective-dated policy versions (partial unique constraint enforces one active version) storing SLA hours (`Low`/`Medium`/`High`), `reminder_lead_hours`, `max_attachments`, closure verification mode (`routine_verification_by`, `escalated_verification_by`), and `notify_on_announcement`.
- `Complaint`: Core aggregate (`tracking_code` unique, `user_id` plain integer, canonical `status` check constraint, `priority` check constraint, orthogonal `is_escalated` + `escalation_type`).
- `ComplaintAttachment`: Validated Google Drive links (`core/files/drive.py`) per complaint.
- `ComplaintHistory`: Append-only chronological status and progress history.
- `ReopenRequest`: Reopening requests for `closed` complaints (partial unique index enforces at most one `pending` request per complaint).
- `ComplaintFeedback`: Post-resolution/closure ratings (`1..5`) and comments (unique per complaint).
- `ComplaintAnnouncement`: Complaint-related announcements published by Handler or Supervisor.
- `CmsNotificationEvent`: Transactional outbox notification events (`dedupe_key` unique) drained by Celery Beat.

## Deployment Order (Step 7.5)
1. `.venv/bin/python manage.py migrate`
2. `.venv/bin/python manage.py seed_cms_policy`
3. `.venv/bin/python manage.py seed_modules`
4. `make permissions` and run `seed_iam_permissions --manifest /path/to/registry/permissions.json` from `Fusion_System_Administrator`
5. `.venv/bin/python manage.py check_cms_readiness` (must print `CMS readiness: OK`)
