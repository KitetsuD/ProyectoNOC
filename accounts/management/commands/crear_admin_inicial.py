import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea o actualiza el primer usuario ADMIN para operar el sistema."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("NOC_ADMIN_USERNAME", "nocadmin"))
        parser.add_argument("--password", default=os.environ.get("NOC_ADMIN_PASSWORD"))
        parser.add_argument("--email", default=os.environ.get("NOC_ADMIN_EMAIL", ""))

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        if not password:
            raise CommandError("Debes entregar --password o definir NOC_ADMIN_PASSWORD.")

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.email = options["email"]
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"ADMIN {username} {action} correctamente."))