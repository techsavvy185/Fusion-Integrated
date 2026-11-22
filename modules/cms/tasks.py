from celery import shared_task

from modules.cms.services.notifications import dispatch_pending_notifications
from modules.cms.services.sla import escalate_breached_complaints, send_pre_breach_reminders


@shared_task(name="cms.send_pre_breach_reminders", acks_late=True)
def run_pre_breach_reminders() -> int:
    return send_pre_breach_reminders()


@shared_task(name="cms.escalate_breached_complaints", acks_late=True)
def run_escalate_breached_complaints() -> int:
    return escalate_breached_complaints()


@shared_task(name="cms.dispatch_notifications", acks_late=True)
def run_dispatch_notifications() -> int:
    return dispatch_pending_notifications()
