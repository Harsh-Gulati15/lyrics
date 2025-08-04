from django.urls import path
from django.contrib.auth import views as auth_views # Use built-in views where possible
from . import views # Your custom views 


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('signup/verify/', views.signup_verify_view, name='signup_verify'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'), # Use built-in logout

    # Password Reset with OTP URLs
    path('password_reset/', views.password_reset_request_view, name='password_reset'),
    path('password_reset/otp/<str:uidb64>/<str:token>/', views.password_reset_otp_view, name='password_reset_otp'),
    path('password_reset/confirm/<str:uidb64>/<str:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password_reset/done/', views.password_reset_done_view, name='password_reset_done'),

]