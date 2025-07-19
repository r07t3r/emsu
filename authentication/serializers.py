
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.models import User, School
import random
import string


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    school_name = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'user_type', 
            'phone_number', 'password', 'password_confirm', 'school_name'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        school_name = validated_data.pop('school_name', None)
        
        user = User.objects.create_user(**validated_data)
        
        # Create school if proprietor and school name provided
        if user.user_type == 'proprietor' and school_name:
            from core.models import School, ProprietorProfile
            school = School.objects.create(
                name=school_name,
                email=user.email,
                phone=user.phone_number or '',
                address='',
                city='',
                state='',
                school_type='both',
                ownership_type='private'
            )
            proprietor_profile = ProprietorProfile.objects.create(user=user)
            proprietor_profile.schools.add(school)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class OTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    
    def validate_phone_number(self, value):
        # Basic phone number validation
        if not value.startswith('+'):
            value = '+234' + value.lstrip('0')
        return value


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(validators=[validate_password])
    password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'phone_number', 'profile_picture', 
            'is_verified', 'email_verified', 'phone_verified',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'email', 'user_type', 'created_at', 'last_login']
