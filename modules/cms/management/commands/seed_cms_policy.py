from django.core.management.base import BaseCommand

from modules.cms.domain.rules import VERIFY_COMPLAINANT, VERIFY_SUPERVISOR
from modules.cms.models import CmsPolicy, ComplaintCategory
from modules.cms.services.policy import create_category, publish_policy

DEFAULT_CATEGORIES = [
    ("NET", "Network & Wi-Fi", "Campus internet, LAN, and Wi-Fi issues"),
    ("ELEC", "Electrical", "Power outages, lighting, fans, and electrical faults"),
    ("CIVIL", "Civil & Plumbing", "Water supply, plumbing, and building repairs"),
    ("HOSTEL", "Hostel & Mess", "Hostel facilities, housekeeping, and mess issues"),
    ("ACAD", "Academic Facilities", "Classroom, lab equipment, and academic support"),
]


class Command(BaseCommand):
    help = "Seed initial effective-dated CMS policy and default complaint categories idempotently."

    def handle(self, *args, **options):
        created_cats = 0
        for code, name, desc in DEFAULT_CATEGORIES:
            if not ComplaintCategory.objects.filter(code=code).exists():
                create_category(code=code, name=name, description=desc)
                created_cats += 1

        if not CmsPolicy.objects.filter(is_active=True).exists():
            publish_policy(
                actor_user_id=0,
                low_sla_hours=72,
                medium_sla_hours=48,
                high_sla_hours=24,
                reminder_lead_hours=4,
                max_attachments=5,
                routine_verification_by=VERIFY_COMPLAINANT,
                escalated_verification_by=VERIFY_SUPERVISOR,
                notify_on_announcement=True,
            )
            self.stdout.write(self.style.SUCCESS("Seeded initial CMS policy (v1)."))
        else:
            self.stdout.write("Active CMS policy already present; left unchanged.")
        self.stdout.write(
            self.style.SUCCESS(f"CMS categories ready ({created_cats} created).")
        )
