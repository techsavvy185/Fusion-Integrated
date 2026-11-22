from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.cms.domain.rules import actor_matches_verifier, required_verifier
from modules.cms.domain.state_machine import (
    CLOSED,
    COMPLAINANT,
    HANDLER,
    IN_PROGRESS,
    REJECTED,
    RESOLVED,
    SUPERVISOR,
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
    check_transition,
)
from modules.cms.models import Complaint, ComplaintHistory
from modules.cms.services.notifications import enqueue_notification

logger = logging.getLogger(__name__)


def _guard_message(guard: str) -> tuple[str, str]:
    messages = {
        "has_handling_setup": (
            "handling_setup_required",
            "Assign and prioritize the complaint before updating progress or resolving it.",
        ),
        "has_progress_note": (
            "progress_note_required",
            "Provide a progress note when updating complaint progress.",
        ),
        "has_resolution_details": (
            "resolution_details_required",
            "Provide resolution details before marking the complaint resolved.",
        ),
        "has_rejection_reason": (
            "rejection_reason_required",
            "Provide a rejection reason before rejecting the complaint.",
        ),
        "matches_required_verifier": (
            "verifier_mismatch",
            "This complaint requires closure verification by the designated role.",
        ),
        "has_pending_reopen_request": (
            "reopen_request_required",
            "An active reopening request is required to reopen a closed complaint.",
        ),
    }
    return messages.get(guard, ("guard_failed", f"Transition guard {guard} failed."))


def _transition_locked(
    *,
    complaint: Complaint,
    to_status: str,
    actor_kind: str,
    actor_user_id: int,
    actor_role: str,
    passed_guards: dict[str, bool],
    event_type: str,
    note: str,
) -> Complaint:
    # Single transactional choke point for all lifecycle state moves (Step 4.4).
    from_status = complaint.status
    try:
        check_transition(from_status, to_status, actor_kind, passed_guards)
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    except ActorNotAllowed as exc:
        raise PermissionDeniedError(str(exc), code="actor_not_allowed") from exc
    except GuardFailed as exc:
        code, msg = _guard_message(exc.guard)
        raise DomainError(msg, code=code) from exc

    complaint.status = to_status
    complaint.save()
    ComplaintHistory.objects.create(
        complaint=complaint,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    return complaint


def resolve_complaint(*, actor, complaint_id: int, resolution_details: str) -> Complaint:
    # UC-CMS-006, CFR-CMS-004, AFR-CMS-023, AFR-CMS-025, BR-CMS-013, BW-CMS-01: resolve complaint.
    details = (resolution_details or "").strip()
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("policy")
            .filter(pk=complaint_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        if complaint.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot resolve your own complaint.", code="self_action_forbidden"
            )
        complaint.resolution_details = details
        complaint.resolved_at = timezone.now()
        complaint.resolved_by_user_id = actor.user_id
        _transition_locked(
            complaint=complaint,
            to_status=RESOLVED,
            actor_kind=HANDLER,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "Complaint Handler",
            passed_guards={
                "has_handling_setup": complaint.has_handling_setup,
                "has_resolution_details": bool(details),
            },
            event_type="resolved",
            note=details,
        )
        enqueue_notification(
            event_type="complaint_resolved",
            subject=f"Complaint {complaint.tracking_code} resolved",
            message=f"Complaint {complaint.tracking_code} has been marked resolved.",
            dedupe_key=f"cms:resolved:{complaint.id}:{complaint.reopen_count}",
            recipient_user_id=complaint.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.resolved complaint_id=%d actor_id=%d", complaint.id, actor.user_id
    )
    return complaint


def reject_complaint(*, actor, complaint_id: int, rejection_reason: str) -> Complaint:
    # UC-CMS-006, CFR-CMS-004, AFR-CMS-024, AFR-CMS-025, BR-CMS-014, BW-CMS-04: reject complaint.
    reason = (rejection_reason or "").strip()
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("policy")
            .filter(pk=complaint_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        if complaint.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot reject your own complaint.", code="self_action_forbidden"
            )
        complaint.rejection_reason = reason
        complaint.rejected_at = timezone.now()
        complaint.rejected_by_user_id = actor.user_id
        _transition_locked(
            complaint=complaint,
            to_status=REJECTED,
            actor_kind=HANDLER,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "Complaint Handler",
            passed_guards={"has_rejection_reason": bool(reason)},
            event_type="rejected",
            note=reason,
        )
        enqueue_notification(
            event_type="complaint_rejected",
            subject=f"Complaint {complaint.tracking_code} rejected",
            message=f"Complaint {complaint.tracking_code} has been rejected.",
            dedupe_key=f"cms:rejected:{complaint.id}",
            recipient_user_id=complaint.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.rejected complaint_id=%d actor_id=%d", complaint.id, actor.user_id
    )
    return complaint


def verify_and_close_complaint(*, actor, complaint_id: int, note: str = "") -> Complaint:
    # UC-CMS-007, UC-CMS-019, CFR-CMS-005, AFR-CMS-027..029, BR-CMS-016, BR-CMS-017.
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("policy")
            .filter(pk=complaint_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        is_supervisor = actor.has_permission("cms.escalation.view")
        if not is_supervisor and complaint.user_id != actor.user_id:
            raise NotFoundError("Complaint not found.", code="complaint_not_found")
        actor_kind = SUPERVISOR if is_supervisor else COMPLAINANT
        mode = required_verifier(complaint.is_escalated, complaint.policy.to_snapshot())
        matches = actor_matches_verifier(actor_kind, mode)
        complaint.closed_at = timezone.now()
        complaint.verified_by_user_id = actor.user_id
        complaint.verified_by_role = actor.active_role or actor_kind
        _transition_locked(
            complaint=complaint,
            to_status=CLOSED,
            actor_kind=actor_kind,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or actor_kind,
            passed_guards={"matches_required_verifier": matches},
            event_type="closed",
            note=(note or "").strip() or "Resolution verified and complaint closed.",
        )
        enqueue_notification(
            event_type="complaint_closed",
            subject=f"Complaint {complaint.tracking_code} closed",
            message=f"Complaint {complaint.tracking_code} has been verified and closed.",
            dedupe_key=f"cms:closed:{complaint.id}:{complaint.reopen_count}",
            recipient_user_id=complaint.user_id,
            complaint=complaint,
        )
    logger.info(
        "cms.complaint.closed complaint_id=%d actor_id=%d", complaint.id, actor.user_id
    )
    return complaint


def transition_to_in_progress_locked(
    *,
    complaint: Complaint,
    actor_kind: str,
    actor_user_id: int,
    actor_role: str,
    passed_guards: dict[str, bool],
    event_type: str,
    note: str,
) -> Complaint:
    return _transition_locked(
        complaint=complaint,
        to_status=IN_PROGRESS,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        passed_guards=passed_guards,
        event_type=event_type,
        note=note,
    )
