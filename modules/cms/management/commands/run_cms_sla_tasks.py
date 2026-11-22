from django.core.management.base import BaseCommand

from modules.cms.services.notifications import dispatch_pending_notifications
from modules.cms.services.sla import escalate_breached_complaints, send_pre_breach_reminders


class Command(BaseCommand):
    help = "Manually run CMS SLA reminder, escalation, and notification dispatch tasks."

    def handle(self, *args, **options):
        reminded = send_pre_breach_reminders()
        escalated = escalate_breached_complaints()
        dispatched = dispatch_pending_notifications()
        self.stdout.write(
            self.style.SUCCESS(
                f"CMS tasks: reminded={reminded} escalated={escalated} dispatched={dispatched}"
            )
        )
