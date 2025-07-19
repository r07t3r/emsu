
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
import logging
import random
import string
from datetime import timedelta

from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    OTPSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer
)
from core.models import User
from core.services.sms import send_sms
from core.utils.notifications import create_notification

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    Advanced user registration with comprehensive validation and security features
    """
    permission_classes = [permissions.AllowAny]
    
    @transaction.atomic
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                # Send welcome email
                self._send_welcome_email(user)
                
                # Create welcome notification
                create_notification(
                    recipient=user,
                    title="Welcome to EMSU!",
                    message="Your account has been created successfully. Please verify your email.",
                    notification_type="success"
                )
                
                # Log registration
                logger.info(f"New user registered: {user.email} ({user.user_type})")
                
                return Response({
                    'message': 'Registration successful',
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(access_token),
                        'refresh': str(refresh)
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return Response({
                    'error': 'Registration failed. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_welcome_email(self, user):
        """Send welcome email to new user"""
        try:
            subject = 'Welcome to EMSU - Educational Management System'
            message = f"""
            Dear {user.get_full_name()},
            
            Welcome to EMSU! Your account has been created successfully.
            
            Please verify your email address to complete your registration.
            
            Best regards,
            EMSU Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")


class LoginView(APIView):
    """
    Advanced login with rate limiting and security features
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Rate limiting
        client_ip = self._get_client_ip(request)
        login_attempts_key = f"login_attempts_{client_ip}"
        attempts = cache.get(login_attempts_key, 0)
        
        if attempts >= 5:  # Max 5 attempts per hour
            return Response({
                'error': 'Too many login attempts. Please try again later.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check if account is locked
            if user.account_locked_until and user.account_locked_until > timezone.now():
                return Response({
                    'error': 'Account is temporarily locked. Please try again later.'
                }, status=status.HTTP_423_LOCKED)
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login_ip = client_ip
            user.save(update_fields=['failed_login_attempts', 'account_locked_until', 'last_login_ip'])
            
            # Clear rate limiting
            cache.delete(login_attempts_key)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Log successful login
            logger.info(f"User logged in: {user.email} from IP: {client_ip}")
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)
        
        else:
            # Increment rate limiting counter
            cache.set(login_attempts_key, attempts + 1, 3600)  # 1 hour
            
            # Handle failed login for existing user
            email = request.data.get('email')
            if email:
                try:
                    user = User.objects.get(email=email)
                    user.failed_login_attempts += 1
                    
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.account_locked_until = timezone.now() + timedelta(hours=1)
                    
                    user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
                except User.DoesNotExist:
                    pass
            
            logger.warning(f"Failed login attempt from IP: {client_ip} for email: {email}")
            
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SendOTPView(APIView):
    """
    Send OTP for phone verification
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            
            # Store OTP in cache (valid for 10 minutes)
            cache_key = f"otp_{phone_number}"
            cache.set(cache_key, otp, 600)
            
            # Send SMS
            message = f"Your EMSU verification code is: {otp}. Valid for 10 minutes."
            
            try:
                send_sms(phone_number, message)
                logger.info(f"OTP sent to {phone_number}")
                
                return Response({
                    'message': 'OTP sent successfully'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Failed to send OTP to {phone_number}: {str(e)}")
                return Response({
                    'error': 'Failed to send OTP. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    """
    Verify OTP for phone verification
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        
        if not phone_number or not otp:
            return Response({
                'error': 'Phone number and OTP are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check OTP
        cache_key = f"otp_{phone_number}"
        stored_otp = cache.get(cache_key)
        
        if stored_otp and stored_otp == otp:
            # Mark phone as verified
            user = request.user
            user.phone_verified = True
            user.phone_number = phone_number
            user.save(update_fields=['phone_verified', 'phone_number'])
            
            # Clear OTP from cache
            cache.delete(cache_key)
            
            return Response({
                'message': 'Phone verified successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Invalid or expired OTP'
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    """
    Request password reset
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Send reset email
            self._send_reset_email(user, token, uid)
            
            return Response({
                'message': 'Password reset email sent'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_reset_email(self, user, token, uid):
        """Send password reset email"""
        try:
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            
            subject = 'Password Reset - EMSU'
            message = f"""
            Dear {user.get_full_name()},
            
            You have requested to reset your password for your EMSU account.
            
            Please click the following link to reset your password:
            {reset_url}
            
            If you did not request this, please ignore this email.
            
            Best regards,
            EMSU Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Failed to send reset email to {user.email}: {str(e)}")


class LogoutView(APIView):
    """
    Logout user and blacklist token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_view(request):
    """
    Get user profile
    """
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)
