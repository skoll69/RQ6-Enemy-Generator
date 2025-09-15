from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = "Run 'migrate --fake-initial' to reconcile existing tables with migrations. Useful when DB already has Django tables from a dump."

    def add_arguments(self, parser):
        # Do NOT re-add Django's global options like --verbosity/--noinput to avoid argparse conflicts.
        parser.add_argument('--database', default='default', help='Database alias to use (default: default)')
        parser.add_argument('--interactive', action='store_true', help='Prompt before executing (default: non-interactive)')

    def handle(self, *args, **options):
        db = options.get('database') or 'default'
        interactive = options.get('interactive', False)
        try:
            connections[db].cursor()
        except OperationalError as e:
            self.stderr.write(self.style.ERROR(f"Database connection failed: {e}"))
            return 1
        self.stdout.write(self.style.WARNING("Running: migrate --fake-initial"))
        call_command('migrate', fake_initial=True, database=db, interactive=interactive)
        self.stdout.write(self.style.SUCCESS("Migrations completed (with --fake-initial)."))
