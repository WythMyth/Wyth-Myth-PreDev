from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Sends a test email using the configured SMTP server'

    def handle(self, *args, **kwargs):
        try:
            send_mail(
                subject='Test Email',
                message='This is a test email sent from Django using Namecheap SMTP.',
                from_email='info@hfallrealty.com',
                recipient_list=['malaminmiu@gmail.com'],
                fail_silently=False,
            )
        except Exception as error:
            print(error)