from django.core.management.base import BaseCommand
from users.views import send_review_reminders

class Command(BaseCommand):
    help = 'Send reminder emails for decks with due cards'

    def handle(self, *args, **options):
        self.stdout.write('Sending review reminders...')
        reminders_sent = send_review_reminders()
        self.stdout.write(self.style.SUCCESS(f'Successfully sent {reminders_sent} review reminders')) 