# Complaint Management System (`cms`) — Quality Report

This document records verified evidence for `modules/cms/`, `client/src/modules/cms/`, and `client/e2e/cms/` on branch `module/cms`.

## 1. CI Gates (`make check` & `make check-client`)

### `make check`
```text
.venv/bin/python manage.py check -> System check identified no issues (0 silenced).
.venv/bin/python manage.py makemigrations --check --dry-run -> No changes detected
.venv/bin/ruff check . -> All checks passed!
.venv/bin/lint-imports -> Contracts: 5 kept, 0 broken.
.venv/bin/python ops/checks/no_cross_module_fk.py -> no cross-module foreign keys
.venv/bin/python ops/checks/contracts_are_plural.py -> all contract getters are plural
.venv/bin/python ops/checks/nav_matches_routes.py -> nav items and client routes agree
.venv/bin/python manage.py permission_manifest --check -> permission manifest matches the registries
make schema-check -> openapi schema matches the code
.venv/bin/python -m pytest -q -> 453 passed [100%]
```

### `make check-client`
```text
tsc --noEmit && tsc --noEmit -p e2e -> 0 errors
vitest run -> 14 test files passed, 69 tests passed
vite build -> built cleanly; largest CMS page chunk: PolicyPage 1.73 kB gzip, ComplaintsPage 1.57 kB gzip (well under 150 kB gzip limit)
```

## 2. Coverage Runs (Step 5.14)

- **Module branch coverage (`--cov=modules/cms --cov-branch --cov-fail-under=90`)**:
  `TOTAL 1323 stmts, 72 miss, 218 branch, 40 partial -> 92.34%` (PASS, >= 90%).
- **Domain branch coverage (`--cov=modules/cms/domain --cov-branch --cov-fail-under=95`)**:
  `TOTAL 159 stmts, 0 miss, 60 branch, 0 partial -> 100.00%` (PASS, >= 95%).

## 3. Test Counts per File & Journey Mapping

| File | Tests | Scope |
|---|---:|---|
| `modules/cms/tests/test_domain.py` | 5 | Pure Python domain validation, SLA math, policy invariants |
| `modules/cms/tests/test_state_machine.py` | 2 | Exhaustive legal/illegal state transition enumeration |
| `modules/cms/tests/test_privilege_escalation.py` | 6 | 401, both gates separately, role boundaries, role switch, CSRF, permission drift |
| `modules/cms/tests/test_scoping_isolation.py` | 2 | Cross-user 404 isolation, hostile query param 400 checks |
| `modules/cms/tests/test_concurrency.py` | 2 | Multi-threaded barrier tests for reopen uniqueness & feedback uniqueness |
| `modules/cms/tests/test_query_budgets.py` | 1 | Constant query counts between 2 and 20 rows across all 4 list endpoints |
| `modules/cms/tests/test_schedule.py` | 3 | Beat registration, idempotency, concurrent SLA auto-escalation |
| `modules/cms/tests/test_journeys.py` | 5 | HTTP end-to-end journeys for `UC-CMS-001`..`017`, `UC-CMS-019`..`022`, `BW-CMS-01`..`08`, `CW-CMS-01`..`03` |
| `modules/cms/tests/test_client_route_guards.py` | 2 | Client `routes.tsx` permission guards match `registry.py` nav permissions |

## 4. Five Broken-on-Purpose Rules Caught by Tests (Step 5.15)

| Rule Mutated | File Mutated | Test That Caught It |
|---|---|---|
| 1. Complainant scoping filter (`UC-CMS-002`) | `modules/cms/selectors/scoping.py` | `test_scoping_isolation.py::test_complainant_isolation_returns_404_never_403` |
| 2. Permission gate on complaint create (`BR-CMS-001`) | `modules/cms/api/views.py` | `test_privilege_escalation.py::test_role_boundaries_handler_supervisor_admin_and_self_action` |
| 3. State machine illegal transition refusal (`BR-CMS-012`) | `modules/cms/domain/state_machine.py` | `test_state_machine.py::test_every_illegal_transition_is_refused` |
| 4. Attachment max count check (`BR-CMS-004`/`005`) | `modules/cms/domain/rules.py` | `test_domain.py::test_validate_attachments_and_priority_and_setup` |
| 5. SLA breach auto-escalation threshold (`BR-CMS-029`) | `modules/cms/domain/sla.py` | `test_schedule.py::test_sla_reminder_and_auto_escalation_and_dispatch_are_idempotent` |

## 5. Adversarial Pass (Step 5.11)

- **Self-action / self-approval:** Verified handler cannot assign/resolve/reject/escalate their own complaint (`self_action_forbidden` 403) and supervisor cannot decide their own reopen request (`test_privilege_escalation.py`).
- **Out-of-scope row access by ID:** Verified Complainant B receives 404 (not 403) on detail, verify-close, feedback, and reopen-request endpoints for Complainant A's complaint (`test_scoping_isolation.py`).
- **Terminal state immutability:** Verified a `rejected` complaint refuses subsequent resolve/escalate/progress actions with 409 (`test_journeys.py`).
- **Duplicate submissions under concurrency:** Verified concurrent reopen requests and concurrent feedback submissions allow exactly one row via DB partial/unique constraints (`test_concurrency.py`).
- **Hostile query parameters:** Verified bad `?status=`, `?priority=`, `?escalated=`, `?category_id=` return 400, never 500 (`test_scoping_isolation.py`).

## 6. Security Self-Audit (Step 7.7)

- Every view sits behind `[HasModuleGrant("cms"), HasPermission(...)]` (zero `AllowAny`).
- Every serializer declares explicit `fields` and marks all server-owned fields read-only.
- Every read starts in `modules/cms/selectors/scoping.py` (404 out of scope).
- Zero raw SQL, `.extra()`, `eval`, `pickle`, `yaml.load`, or `subprocess` on request data.
- Attachment URLs validated via `core/files/drive.py::parse` and filename labels sanitised via `core/files/validators.py::sanitise_filename`.
- Every write view sets `throttle_scope = "cms_write"`.
- Logs emit integer IDs only (no names, roll numbers, tokens, or request bodies).
- Cookie-authenticated write without `X-CSRF-Token` verified to return 403 (`test_privilege_escalation.py`).
- Client uses `lib/http.ts` exclusively, zero `dangerouslySetInnerHTML`, zero `any`, zero `console.log`, zero new dependencies.
- Production deploy check (`DJANGO_SETTINGS_MODULE=config.settings.prod ... manage.py check --deploy --fail-level WARNING`): `System check identified no issues (2 silenced).`

## 7. Fresh-Install Proof (Step 7.8)

Executed end-to-end against throwaway database `fusion_integrated_fresh`:
```text
Applying cms.0001_initial... OK
Unapplying cms.0001_initial... OK
Applying cms.0001_initial... OK
cms: registered but NOT active — 2 prerequisite(s) unmet:
    No active CMS policy exists — run '.venv/bin/python manage.py seed_cms_policy'.
    No active CMS categories — run manage.py seed_cms_policy.
Seeded initial CMS policy (v1).
CMS categories ready (5 created).
registered cms (active)
CMS readiness: OK
CMS tasks: reminded=0 escalated=0 dispatched=0
```
Throwaway database `fusion_integrated_fresh` was dropped cleanly after verification.

## 8. Browser Walkthrough & Playwright E2E Verification (Step 6.9)

Executed `make e2e` against live IAM (`:8001`), live `make dev` (`:8002`), and Vite (`:5173`): **`21 passed (9.0s)`** (zero console errors, zero 500s, including keyboard-only complaint submission and all 5 guarded route deep-link refusals).

| Role | Synthetic Account | Use Cases Covered | Spec File | Result |
|---|---|---|---|---|
| Plain User (`student`) | `stu00001` | `UC-CMS-001`, `UC-CMS-002`, `UC-CMS-014`, Keyboard-only Tab+Enter flow, Guarded routes (`/cms/escalations`, `/cms/reopen-requests`, `/cms/feedback`, `/cms/reports`, `/cms/policy`) | `client/e2e/cms/complaints.spec.ts`, `client/e2e/cms/lifecycle.spec.ts`, `client/e2e/cms/route-guards.spec.ts` | **PASS** |
| `Complaint Handler` | `stf00063` | `UC-CMS-003`, `UC-CMS-004`, `UC-CMS-005`, `UC-CMS-006`, `UC-CMS-010`, `UC-CMS-013`, `UC-CMS-015` | `client/e2e/cms/lifecycle.spec.ts`, `client/e2e/cms/handler-and-supervisor.spec.ts` | **PASS** |
| `Complaint Supervisor` | `fac00001` | `UC-CMS-012`, `UC-CMS-016`, `UC-CMS-020` | `client/e2e/cms/handler-and-supervisor.spec.ts` | **PASS** |
| `adminstrator` | `stf00064` | `UC-CMS-017`, CMS Policy & Categories | `client/e2e/cms/handler-and-supervisor.spec.ts` | **PASS** |

### Captured `runserver` Request Logs from Browser Walkthrough (`make e2e`)
```text
[23/Nov/2026 17:42:45] "GET /api/v1/cms/categories/ HTTP/1.1" 200 919
[23/Nov/2026 17:42:46] "GET /api/v1/cms/announcements/ HTTP/1.1" 200 707
[23/Nov/2026 17:42:47] "POST /api/v1/cms/complaints/ HTTP/1.1" 201 1093
[23/Nov/2026 17:42:48] "POST /api/v1/cms/announcements/ HTTP/1.1" 201 221
[23/Nov/2026 17:42:48] "GET /api/v1/cms/complaints/?escalated=true HTTP/1.1" 200 42
[23/Nov/2026 17:42:48] "GET /api/v1/cms/reports/analytics/ HTTP/1.1" 200 451
[23/Nov/2026 17:42:48] "GET /api/v1/cms/reopen-requests/ HTTP/1.1" 200 42
[23/Nov/2026 17:42:48] "GET /api/v1/cms/policy/ HTTP/1.1" 200 418
[23/Nov/2026 17:42:49] "GET /api/v1/cms/reports/operational/ HTTP/1.1" 200 238
[23/Nov/2026 17:42:49] "GET /api/v1/cms/reports/escalations/ HTTP/1.1" 200 192
[23/Nov/2026 17:42:50] "POST /api/v1/cms/complaints/ HTTP/1.1" 201 1099
[23/Nov/2026 17:42:50] "POST /api/v1/cms/complaints/4/handling-setup/ HTTP/1.1" 200 1408
[23/Nov/2026 17:42:50] "POST /api/v1/cms/complaints/4/progress/ HTTP/1.1" 200 1640
[23/Nov/2026 17:42:51] "POST /api/v1/cms/complaints/4/resolve/ HTTP/1.1" 200 1903
[23/Nov/2026 17:42:51] "GET /api/v1/cms/feedback/ HTTP/1.1" 200 42
```

## 9. Manual Execution of Scheduled Tasks

Executed via `.venv/bin/python manage.py run_cms_sla_tasks` and verified in `modules/cms/tests/test_schedule.py`:
- `cms.send_pre_breach_reminders`: stamps `reminder_sent_at` and enqueues 1 deduplicated `sla_pre_breach_reminder` event; second run returns `0`.
- `cms.escalate_breached_complaints`: sets `is_escalated=True`, `escalation_type="automatic"`, writes `ComplaintHistory`, and enqueues 1 deduplicated `complaint_escalated` event; second run and concurrent run return `0`.
- `cms.dispatch_notifications`: stamps `dispatched_at` on pending outbox rows; second run returns `0`.

## 10. Accepted Known Gaps

| Spec IDs | Reason | Approval Record |
|---|---|---|
| `CFR-CMS-013`, `AFR-CMS-064..068`, `UC-CMS-018`, `BR-CMS-035`, `BR-CMS-036`, `BR-CMS-037` | Fusion ADR-0002 forbids domain modules from owning `Role`/`Permission`/`UserRole` tables or writing to `fusionlab`/`fusion_system_db`; role assignment/reassignment/cardinality belongs exclusively to `Fusion_System_Administrator` (IAM/ERP). | Approved by Student 2 on 2026-11-23 along with `docs/19-cms/cms-blueprint.md` (Section (h)). |

## 11. Recorded Approvals

- **Blueprint, `ISS-CMS-007..010` resolutions, accepted IAM gap (`UC-CMS-018`/`BR-CMS-035..037`), and new ERP designations (`Complaint Handler`, `Complaint Supervisor`)**:
  > Dated written approval from Student 2 (2026-11-23, pair review): Approved `docs/19-cms/cms-blueprint.md` (including `NN=19`, `ISS-CMS-007..010` design decisions, Option A IAM role mapping, and Option A accepted known gap for `UC-CMS-018`/`BR-CMS-035..037`).
- **Shared-file registrations:** Limited strictly to pre-approved Step 4.0 registration files (`config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, `client/e2e/accounts.ts`, `ops/docs/cms_reference.py`, `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`).
- **New dependencies:** None.

## 12. Review Round Scorecards

*(To be populated after each independent review round in Step 7; final round scorecard goes in the PR description.)*
