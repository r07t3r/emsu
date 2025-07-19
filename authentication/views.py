from django.shortcuts import render

# Create your views here.
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer
from core.services.sms import send_sms

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        user = authenticate(email=data.get('email'), password=data.get('password'))
        if not user:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })

class SendOTPView(generics.GenericAPIView):
    """
    Endpoint: /api/v1/auth/send-otp/
    Payload: {"phone":"+2348012345678", "message":"Your OTP is 1234"}
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone   = request.data['phone']
        message = request.data['message']
        result = send_sms(phone, message)
        return Response({'status': result}, status=status.HTTP_200_OK)
