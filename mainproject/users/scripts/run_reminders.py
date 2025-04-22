from django.utils import timezone
from users.views import send_review_reminders
from django.conf import settings

def run():
    """Run the reminder sending process manually"""
    print(f"Starting reminder process at {timezone.now()}")
    print(f"Email backend: {settings.EMAIL_BACKEND}")
    print(f"OpenAI API configured: {hasattr(settings, 'OPENAI_API_KEY') and bool(settings.OPENAI_API_KEY)}")
    print(f"Using OpenAI for emails: {getattr(settings, 'USE_OPENAI_FOR_EMAILS', True)}")
    
    # Send the reminders
    reminders_sent = send_review_reminders()
    
    print(f"Sent {reminders_sent} reminders")