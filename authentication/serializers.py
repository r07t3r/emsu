from django.contrib.auth import get_user_model
from rest_framework import serializers
from allauth.account.utils import send_email_confirmation

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data['role']
        )
        # Trigger email verification
        send_email_confirmation(self.context['request'], user)
        return user

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)
