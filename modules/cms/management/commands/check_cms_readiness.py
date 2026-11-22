from django.core.management.base import BaseCommand

from modules.cms.registry import readiness


class Command(BaseCommand):
    help = "Check whether CMS prerequisites (policy and categories) are satisfied."

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            for item in unmet:
                self.stdout.write(self.style.WARNING(f"UNMET: {item}"))
            return
        self.stdout.write(self.style.SUCCESS("CMS readiness: OK"))
