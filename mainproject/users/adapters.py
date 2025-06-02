from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from django.http import HttpResponseRedirect
from allauth.account.utils import user_email, user_field, user_username
from django.shortcuts import redirect

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True

    def get_login_redirect_url(self, request):
        return reverse('users:landing_page')

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user_field(user, 'email', user_email(user))
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.save()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return reverse('users:landing_page')

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Ensure email is set
        if sociallogin.account.provider == 'google':
            email = sociallogin.account.extra_data.get('email')
            if email:
                user.email = email
        return user 