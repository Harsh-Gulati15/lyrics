from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import random # For OTP generation
from .forms import CustomUserCreationForm # Import your custom form
from django.contrib import messages
from .models import RememberMeToken
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import logout as auth_logout # Renamed import
from django.shortcuts import redirect
from django.conf import settings
from .forms import CustomUserCreationForm
import smtplib
from email.message import EmailMessage # <--- ADD THIS LINE
import traceback
import random
from datetime import timedelta

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages

from .forms import CustomUserCreationForm
from django.conf import settings # Import settings
from .models import RememberMeToken # Import your new model


# --- Login and Signup ---
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user) # Standard session login

                # Create a response object first
                response = redirect(settings.LOGIN_REDIRECT_URL or 'dashboard')

                # --- "Remember Me" Logic ---
                if request.POST.get('remember_me'):
                    # Delete any old tokens for this user for security
                    RememberMeToken.objects.filter(user=user).delete()

                    selector, validator = RememberMeToken.generate_token()
                    expires = timezone.now() + timedelta(days=30) # Token lives for 30 days

                    token_instance = RememberMeToken(user=user, selector=selector, expires_at=expires)
                    token_instance.set_validator(validator) # Hashes and sets the validator
                    token_instance.save()

                    # Set the cookie on the response object
                    cookie_value = f"{selector}:{validator}"
                    response.set_cookie(
                        'remember_me_token',
                        cookie_value,
                        expires=expires,
                        httponly=True,  # CRITICAL: Prevents JS access
                        secure=not settings.DEBUG,  # CRITICAL: Send only over HTTPS in production
                        samesite='Lax'
                    )
                    print(f"Remember me cookie set for {user.username}")
                
                return response # Return the response with or without the cookie
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.") # Or show form.errors
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Form is valid, but DON'T save the user yet.
            # Store the cleaned form data in the session to use after OTP verification.
            request.session['unverified_user_data'] = form.cleaned_data

            # Generate and store OTP in the session
            otp = generate_otp()
            request.session['signup_otp'] = otp
            # Store an expiration time for the OTP (e.g., 5 minutes from now)
            request.session['otp_expires_at'] = (timezone.now() + timedelta(minutes=5)).isoformat()

            # --- Send the OTP Email ---
            email = form.cleaned_data.get('email')
            subject = 'Your Verification Code for LyriXFlow'
            message_body = f'Welcome to LyriXFlow! Your one-time verification code is: {otp}\n\nThis code is valid for 5 minutes.'

            # Construct the email message
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = email
            msg.set_content(message_body)

            try:
                print(f"Attempting to send signup OTP to {email}")
                # Using a 'with' statement for automatic connection handling
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    if settings.EMAIL_USE_TLS:
                        server.starttls()
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    server.send_message(msg)
                
                print("Signup OTP email sent successfully.")
                messages.info(request, 'A verification code has been sent to your email.')
                
                # Redirect to the new OTP verification page
                return redirect('signup_verify')

            except Exception as e:
                print(f"!!! Error sending signup OTP: {e}")
                traceback.print_exc()
                messages.error(request, 'We could not send a verification email at this time. Please try again later.')
                # Fall through to re-render the signup form with an error

        else: # Form is not valid
             for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
    else: # GET request
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


# --- NEW: Step 2 of Signup (Verifies OTP, Creates User) ---

def signup_verify_view(request):
    # Retrieve data from the session
    unverified_data = request.session.get('unverified_user_data')
    stored_otp = request.session.get('signup_otp')
    otp_expiry_str = request.session.get('otp_expires_at')

    # If session data is missing, the flow is broken. Redirect to signup.
    if not all([unverified_data, stored_otp, otp_expiry_str]):
        messages.error(request, 'Your verification session has expired or is invalid. Please start the signup process again.')
        return redirect('signup')

    otp_expiry = timezone.datetime.fromisoformat(otp_expiry_str)

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        # 1. Check for OTP Expiry
        if timezone.now() > otp_expiry:
            # Clear session data and redirect
            request.session.flush() # Clears the entire session
            messages.error(request, 'Your verification code has expired. Please sign up again.')
            return redirect('signup')

        # 2. Check if OTP matches
        if entered_otp == stored_otp:
            # OTP is correct. Now, create the user.
            try:
                # Use User.objects.create_user to handle password hashing
                user = User.objects.create_user(
                    username=unverified_data['username'],
                    email=unverified_data['email'],
                    password=unverified_data['password2'] # UserCreationForm puts cleaned pw in password2
                )
                user.save()

                # Clean up session data
                request.session.flush()
                
                messages.success(request, 'Your account has been successfully verified and created! Please log in.')
                return redirect('login')

            except Exception as e:
                # Handle potential race conditions (e.g., username was taken in the meantime)
                print(f"Error creating user after OTP verification: {e}")
                messages.error(request, 'There was an error creating your account. The username or email may have been taken. Please try signing up again.')
                request.session.flush()
                return redirect('signup')
        else:
            # Incorrect OTP
            messages.error(request, 'The verification code you entered is incorrect. Please try again.')
            # Fall through to re-render the OTP form with the error message

    # This handles the initial GET request to the page
    return render(request, 'accounts/signup_otp_verify.html')

# --- OTP Password Reset Views ---

def generate_otp(length=6):
    """Generate a simple numeric OTP."""
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def password_reset_request_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')
            return render(request, 'accounts/password_reset/password_reset_request.html')

        # Generate OTP and token
        otp = generate_otp()
        token = default_token_generator.make_token(user) # Use Django's token generator
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Store OTP in session (simple method, expires with session)
        # A more robust method might use a temporary model or cache
        request.session['password_reset_otp'] = otp
        request.session['password_reset_uid'] = uidb64
        request.session['password_reset_token_check'] = token # Store token to verify later
        request.session.set_expiry(300) # OTP valid for 5 minutes

        # Send Email
        subject = 'Your Password Reset OTP for LyriXFlow'
        message = f'Your OTP is: {otp}\n\nIt is valid for 5 minutes.'
        try:
            # --- Add print statements BEFORE send_mail to ensure this part works ---
            print(f"Attempting to send OTP {otp} to {email} for user {user.username}")
            print(f"UID: {uidb64}, Token: {token}")
            # --- End debug prints ---

            send_mail(subject, message, 'lyrixfloww@gmail.com', [email])

            messages.success(request, 'An OTP has been sent to your email (check console).') # Update message
            return redirect(reverse('password_reset_otp', kwargs={'uidb64': uidb64, 'token': token}))
        except Exception as e:
            # --- PRINT THE ACTUAL EXCEPTION ---
            print(f"!!! Error during password reset email step: {e}")
            print(f"Exception Type: {type(e)}")
            # --- END EXCEPTION PRINT ---
            messages.error(request, 'Error sending email. Please try again.')

    return render(request, 'accounts/password_reset/password_reset_request.html')

def password_reset_otp_view(request, uidb64, token):
    # Basic validation: Check if the token and uid roughly match what's expected from session
    session_uid = request.session.get('password_reset_uid')
    session_token_check = request.session.get('password_reset_token_check')
    if not session_uid or session_uid != uidb64 or not session_token_check or session_token_check != token:
         messages.error(request, 'Invalid or expired password reset link.')
         return redirect('password_reset')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('password_reset_otp')

        if stored_otp and entered_otp == stored_otp:
            # OTP correct, proceed to password set form
            messages.success(request, 'OTP verified successfully.')
            # Keep uid/token for the next step, clear OTP
            del request.session['password_reset_otp']
            return redirect(reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token}))
        else:
            messages.error(request, 'Invalid or expired OTP.')

    return render(request, 'accounts/password_reset/password_reset_otp.html', {'uidb64': uidb64, 'token': token})

def password_reset_confirm_view(request, uidb64, token):
     # Verify session uid/token again
    session_uid = request.session.get('password_reset_uid')
    session_token_check = request.session.get('password_reset_token_check')
    if not session_uid or session_uid != uidb64 or not session_token_check or session_token_check != token:
         messages.error(request, 'Invalid or expired password reset link.')
         return redirect('password_reset')

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Use Django's token generator to verify the user and token validity
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                # Clear session variables
                request.session.pop('password_reset_uid', None)
                request.session.pop('password_reset_token_check', None)
                messages.success(request, 'Your password has been successfully reset. You can now log in.')
                return redirect('login')
            else:
                 for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = SetPasswordForm(user)
        return render(request, 'accounts/password_reset/password_reset_form.html', {'form': form})
    else:
        messages.error(request, 'The password reset link was invalid or has expired.')
        return redirect('password_reset')

def password_reset_done_view(request):
    # This view is simple, just confirms completion if redirected here
    # Usually rendered after a successful password set
    return render(request, 'accounts/password_reset/password_reset_done.html')

def custom_logout_view(request): # If you have a custom view
    if request.user.is_authenticated:
        RememberMeToken.objects.filter(user=request.user).delete()
    auth_logout(request)
    response = redirect(settings.LOGOUT_REDIRECT_URL or 'index')
    response.delete_cookie('remember_me_token')
    messages.info(request, "You have been logged out.")
    return response