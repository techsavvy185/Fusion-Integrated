import threading
from datetime import timedelta

import pytest
from django.db import connections
from django.utils import timezone

from config.celery import app as celery_app
from modules.cms.domain.rules import VERIFY_COMPLAINANT, VERIFY_SUPERVISOR
from modules.cms.domain.state_machine import ESCALATION_AUTOMATIC, IN_PROGRESS
from modules.cms.models import CmsNotificationEvent, Complaint
from modules.cms.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.cms.services.policy import create_category, publish_policy
from modules.cms.tasks import (
    run_dispatch_notifications,
    run_escalate_breached_complaints,
    run_pre_breach_reminders,
)


def test_cms_schedule_and_routes_registered_in_celery():
    # Step 5.9: every beat entry and route in schedule.py is merged into config/celery.py.
    for key in BEAT_SCHEDULE:
        assert key in celery_app.conf.beat_schedule
    for key in TASK_ROUTES:
        assert key in celery_app.conf.task_routes


@pytest.mark.django_db
def test_sla_reminder_and_auto_escalation_and_dispatch_are_idempotent(
    cms_policy, cms_category
):
    # Step 5.9, UC-CMS-021, UC-CMS-022, BR-CMS-028, BR-CMS-029, BW-CMS-08, CW-CMS-03.
    now = timezone.now()
    approaching = Complaint.objects.create(
        tracking_code="CMS-REM00001",
        user_id=101,
        category=cms_category,
        policy=cms_policy,
        title="Approaching SLA",
        description="Due in 2h",
        status=IN_PROGRESS,
        priority="High",
        assigned_to_user_id=202,
        sla_due_at=now + timedelta(hours=2),
    )
    breached = Complaint.objects.create(
        tracking_code="CMS-BRE00001",
        user_id=102,
        category=cms_category,
        policy=cms_policy,
        title="Breached SLA",
        description="Past due",
        status=IN_PROGRESS,
        priority="High",
        assigned_to_user_id=202,
        sla_due_at=now - timedelta(hours=1),
    )

    # First run acts once; second run is a no-op.
    assert run_pre_breach_reminders() == 1
    assert run_pre_breach_reminders() == 0
    approaching.refresh_from_db()
    assert approaching.reminder_sent_at is not None
    assert approaching.is_escalated is False

    assert run_escalate_breached_complaints() == 1
    assert run_escalate_breached_complaints() == 0
    breached.refresh_from_db()
    assert breached.is_escalated is True
    assert breached.escalation_type == ESCALATION_AUTOMATIC

    assert (
        CmsNotificationEvent.objects.filter(
            complaint=approaching, event_type="sla_pre_breach_reminder"
        ).count()
        == 1
    )
    assert (
        CmsNotificationEvent.objects.filter(
            complaint=breached, event_type="complaint_escalated"
        ).count()
        == 1
    )

    assert run_dispatch_notifications() == 2
    assert run_dispatch_notifications() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_auto_escalation_takes_effect_once():
    # Step 5.9: two workers running the SLA breach task simultaneously escalate only once.
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
    cat = create_category(code="SLAC", name="SLA Concurrency")
    c = Complaint.objects.create(
        tracking_code="CMS-SLAC0001",
        user_id=103,
        category=cat,
        policy=pol,
        title="Race SLA",
        description="Past due",
        status=IN_PROGRESS,
        priority="High",
        sla_due_at=timezone.now() - timedelta(minutes=10),
    )
    barrier = threading.Barrier(2)
    counts = []

    def worker():
        try:
            barrier.wait()
            counts.append(run_escalate_breached_complaints())
        finally:
            connections.close_all()

    t1, t2 = threading.Thread(target=worker), threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert sum(counts) == 1
    assert (
        CmsNotificationEvent.objects.filter(
            complaint=c, event_type="complaint_escalated"
        ).count()
        == 1
    )
