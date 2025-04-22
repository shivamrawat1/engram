from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def run():
    """Test email sending functionality"""
    try:
        print("Testing email sending...")
        print(f"Using email settings:")
        print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
        print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Send a test email
        recipient_email = 'shivam@uni.minerva.edu'
        print(f"Sending test email to: {recipient_email}")
        
        # Create a more detailed test message
        subject = "Test Email from Django Flashcard App"
        message = "This is a test email from your Django flashcard application."
        html_message = """
        <html>
        <body>
            <h2>Test Email</h2>
            <p>This is a test email from your Django flashcard application.</p>
            <p>If you're seeing this, email sending is working correctly!</p>
            <hr>
            <p><small>Sent at: {}</small></p>
        </body>
        </html>
        """.format(timezone.now())
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
            html_message=html_message
        )
        print("Test email sent successfully!")
        
        # Try to diagnose any potential issues
        print("\nChecking for common email configuration issues:")
        if settings.EMAIL_HOST_USER == 'shivam16004@gmail.com':
            print("- Using Gmail: Make sure you have an App Password set up if 2FA is enabled")
            print("  Current password length:", len(settings.EMAIL_HOST_PASSWORD))
            if len(settings.EMAIL_HOST_PASSWORD) < 16:
                print("  WARNING: Gmail app passwords are usually 16 characters")
        
        if settings.EMAIL_PORT == 587 and not settings.EMAIL_USE_TLS:
            print("- WARNING: Port 587 typically requires EMAIL_USE_TLS=True")
        
        if settings.EMAIL_PORT == 465 and not getattr(settings, 'EMAIL_USE_SSL', False):
            print("- WARNING: Port 465 typically requires EMAIL_USE_SSL=True")
            
    except Exception as e:
        import traceback
        print(f"Failed to send test email: {str(e)}")
        print(traceback.format_exc()) 