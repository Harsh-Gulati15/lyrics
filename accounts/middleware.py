# accounts/middleware.py
from django.contrib.auth import login
from django.utils import timezone
from .models import RememberMeToken

class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check if user is not already logged in and the cookie exists
        if not request.user.is_authenticated and 'remember_me_token' in request.COOKIES:
            cookie_value = request.COOKIES.get('remember_me_token')
            try:
                selector, validator_from_cookie = cookie_value.split(':', 1)
            except ValueError:
                # Malformed cookie, let the response clear it later
                request.delete_remember_me_cookie = True
                return self.get_response(request)

            try:
                token_instance = RememberMeToken.objects.get(selector=selector)
                # Check for expiration and validator match
                if not token_instance.is_expired() and token_instance.check_validator(validator_from_cookie):
                    user = token_instance.user
                    if user.is_active:
                        # Log the user in for this request
                        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        print(f"Auto-logged in user via remember me token: {user.username}")
                else:
                    # Token is invalid (expired or wrong validator), delete it
                    token_instance.delete()
                    request.delete_remember_me_cookie = True # Signal to delete the cookie
            except RememberMeToken.DoesNotExist:
                # Token not found in DB, something is wrong, delete the cookie
                request.delete_remember_me_cookie = True

        response = self.get_response(request)

        # If a check failed above, delete the bad cookie from the user's browser
        if hasattr(request, 'delete_remember_me_cookie'):
            response.delete_cookie('remember_me_token')

        return response