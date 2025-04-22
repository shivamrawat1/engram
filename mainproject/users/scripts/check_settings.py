from django.conf import settings
import os

def run():
    """Check which settings file is being used"""
    print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"Settings file path: {settings.__file__}")
    
    # Check if our email settings exist
    print("\nEmail settings:")
    print(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
    print(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}")
    print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
    print(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}") 