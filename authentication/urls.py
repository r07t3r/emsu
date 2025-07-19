from django.urls import path
from .views import RegisterView, LoginView, SendOTPView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/',    LoginView.as_view(),    name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
]
