from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from tracker.models import ShortcutToken


class Command(BaseCommand):
    help = "Create a one-time bearer token for Apple Shortcuts."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("name")

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=options["username"])
        except user_model.DoesNotExist as error:
            raise CommandError(f"Unknown username: {options['username']}") from error

        _, raw_token = ShortcutToken.create_token(user, options["name"])
        self.stdout.write(self.style.SUCCESS("Copy this token now; it cannot be shown again:"))
        self.stdout.write(raw_token)
