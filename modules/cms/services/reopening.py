from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.cms.domain.rules import RuleViolation, validate_reopen_request
from modules.cms.domain.sla import compute_sla_due_at
from modules.cms.domain.state_machine import SUPERVISOR
from modules.cms.models import Complaint, ComplaintHistory, ReopenRequest
from modules.cms.services.notifications import enqueue_notification
from modules.cms.services.transitions import transition_to_in_progress_locked

logger = logging.getLogger(__name__)


def request_reopening(*, actor, complaint_id: int, reason: str) -> ReopenRequest:
    # UC-CMS-008, CFR-CMS-006, AFR-CMS-030, BR-CMS-018, CW-CMS-02: complainant requests reopening.
    clean_reason = (reason or "").strip()
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None or complaint.user_id != actor.user_id:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        has_pending = ReopenRequest.objects.filter(
            complaint=complaint, status=ReopenRequest.PENDING
        ).exists()
        try:
            validate_reopen_request(complaint.status, clean_reason, has_pending)
        except RuleViolation as exc:
            if exc.code in ("reopen_requires_closed", "reopen_already_pending"):
                raise ConflictError(exc.message, code=exc.code) from exc
            raise DomainError(exc.message, code=exc.code) from exc
        try:
            req = ReopenRequest.objects.create(
                complaint=complaint,
                requested_by_user_id=actor.user_id,
                reason=clean_reason,
                status=ReopenRequest.PENDING,
            )
        except IntegrityError as exc:
            raise ConflictError(
                "A reopening request is already pending for this complaint.",
                code="reopen_already_pending",
            ) from exc

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or actor.kind,
            event_type="reopen_requested",
            from_status=complaint.status,
            to_status=complaint.status,
            note=clean_reason,
        )
    logger.info("cms.reopen.requested complaint_id=%d request_id=%d", complaint.id, req.id)
    return req


def decide_reopening(
    *, actor, request_id: int, decision: str, decision_note: str = ""
) -> ReopenRequest:
    # UC-CMS-020, CFR-CMS-006, AFR-CMS-031..034, BR-CMS-019..021, BW-CMS-05, BW-CMS-06.
    clean_decision = (decision or "").strip().lower()
    if clean_decision not in ("approve", "deny"):
        raise DomainError("Decision must be 'approve' or 'deny'.", code="invalid_decision")
    clean_note = (decision_note or "").strip()

    with transaction.atomic():
        req = (
            ReopenRequest.objects.select_for_update()
            .select_related("complaint", "complaint__policy")
            .filter(pk=request_id)
            .first()
        )
        if req is None:
            raise NotFoundError(
                "Reopening request not found.", code="reopen_request_not_found"
            )
        if req.requested_by_user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot decide your own reopening request.", code="self_action_forbidden"
            )
        if req.status != ReopenRequest.PENDING:
            raise ConflictError(
                "This reopening request has already been decided.",
                code="reopen_already_decided",
            )

        complaint = (
            Complaint.objects.select_for_update()
            .select_related("policy")
            .get(pk=req.complaint_id)
        )
        now = timezone.now()
        req.decided_by_user_id = actor.user_id
        req.decision_note = clean_note
        req.decided_at = now

        if clean_decision == "approve":
            req.status = ReopenRequest.APPROVED
            req.save()
            complaint.reopen_count += 1
            complaint.last_reopened_at = now
            complaint.closed_at = None
            complaint.resolved_at = None
            complaint.reminder_sent_at = None
            if complaint.priority:
                complaint.sla_due_at = compute_sla_due_at(
                    now, complaint.priority, complaint.policy.to_snapshot()
                )
            transition_to_in_progress_locked(
                complaint=complaint,
                actor_kind=SUPERVISOR,
                actor_user_id=actor.user_id,
                actor_role=actor.active_role or "Complaint Supervisor",
                passed_guards={"has_pending_reopen_request": True},
                event_type="reopen_approved",
                note=clean_note or "Reopening request approved.",
            )
            enqueue_notification(
                event_type="complaint_reopen_approved",
                subject=f"Complaint {complaint.tracking_code} reopened",
                message=f"Your reopening request for {complaint.tracking_code} was approved.",
                dedupe_key=f"cms:reopen_decided:{req.id}",
                recipient_user_id=complaint.user_id,
                complaint=complaint,
            )
        else:
            req.status = ReopenRequest.DENIED
            req.save()
            ComplaintHistory.objects.create(
                complaint=complaint,
                actor_user_id=actor.user_id,
                actor_role=actor.active_role or "Complaint Supervisor",
                event_type="reopen_denied",
                from_status=complaint.status,
                to_status=complaint.status,
                note=clean_note or "Reopening request denied.",
            )
            enqueue_notification(
                event_type="complaint_reopen_denied",
                subject=f"Reopening request denied for {complaint.tracking_code}",
                message=f"Your reopening request for {complaint.tracking_code} was denied.",
                dedupe_key=f"cms:reopen_decided:{req.id}",
                recipient_user_id=complaint.user_id,
                complaint=complaint,
            )
    logger.info(
        "cms.reopen.decided request_id=%d decision=%s actor_id=%d",
        req.id,
        clean_decision,
        actor.user_id,
    )
    return req
