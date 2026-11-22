import threading

import pytest
from django.db import connections

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.cms.domain.rules import VERIFY_COMPLAINANT, VERIFY_SUPERVISOR
from modules.cms.domain.state_machine import CLOSED, RESOLVED
from modules.cms.models import Complaint, ComplaintFeedback, ReopenRequest
from modules.cms.registry import ROLE_GRANTS
from modules.cms.services.feedback import submit_feedback
from modules.cms.services.policy import create_category, publish_policy
from modules.cms.services.reopening import request_reopening


@pytest.mark.django_db(transaction=True)
def test_concurrent_reopen_requests_only_one_succeeds():
    # Step 5.7, BR-CMS-018: partial unique index prevents duplicate pending reopen requests under concurrency.
    pol = publish_policy(
        actor_user_id=999,
        low_sla_hours=72,
        medium_sla_hours=48,
        high_sla_hours=24,
        reminder_lead_hours=4,
        max_attachments=3,
        routine_verification_by=VERIFY_COMPLAINANT,
        escalated_verification_by=VERIFY_SUPERVISOR,
        notify_on_announcement=True,
    )
    cat = create_category(code="CONC", name="Concurrency Cat")
    complaint = Complaint.objects.create(
        tracking_code="CMS-CONC0001",
        user_id=701,
        category=cat,
        policy=pol,
        title="Closed item",
        description="Desc",
        status=CLOSED,
    )
    actor = make_principal(
        user_id=701, permissions=tuple(ROLE_GRANTS["student"]), modules=("cms",)
    )

    barrier = threading.Barrier(2)
    results = []

    def worker():
        try:
            barrier.wait()
            request_reopening(
                actor=actor, complaint_id=complaint.id, reason="Concurrent reopen"
            )
            results.append("ok")
        except ConflictError as exc:
            results.append(type(exc).__name__)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1
    assert ReopenRequest.objects.filter(complaint=complaint, status="pending").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_feedback_only_one_succeeds():
    # Step 5.7, BR-CMS-022: unique constraint prevents duplicate feedback under concurrent submissions.
    pol = publish_policy(
        actor_user_id=999,
        low_sla_hours=72,
        medium_sla_hours=48,
        high_sla_hours=24,
        reminder_lead_hours=4,
        max_attachments=3,
        routine_verification_by=VERIFY_COMPLAINANT,
        escalated_verification_by=VERIFY_SUPERVISOR,
        notify_on_announcement=True,
    )
    cat = create_category(code="CONCFB", name="Concurrency Feedback")
    complaint = Complaint.objects.create(
        tracking_code="CMS-CONC0002",
        user_id=702,
        category=cat,
        policy=pol,
        title="Resolved item",
        description="Desc",
        status=RESOLVED,
    )
    actor = make_principal(
        user_id=702, permissions=tuple(ROLE_GRANTS["student"]), modules=("cms",)
    )

    barrier = threading.Barrier(2)
    results = []

    def worker():
        try:
            barrier.wait()
            submit_feedback(actor=actor, complaint_id=complaint.id, rating=5, comment="Fast")
            results.append("ok")
        except ConflictError as exc:
            results.append(type(exc).__name__)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1
    assert ComplaintFeedback.objects.filter(complaint=complaint).count() == 1
