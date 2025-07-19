from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, SendOTPView, VerifyOTPView,
    PasswordResetView, profile_view
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('profile/', profile_view, name='auth-profile'),
]
