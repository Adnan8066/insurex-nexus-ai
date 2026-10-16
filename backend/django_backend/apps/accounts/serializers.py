from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from django.db import transaction
from django.utils.text import slugify
from .models import User, UserProfile, Role

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'date_of_birth', 'emergency_contact_name',
            'emergency_contact_phone', 'preferred_language', 'timezone',
            'notification_email', 'notification_sms', 'notification_push',
        ]
        read_only_fields = ['created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    full_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'name',
            'role', 'phone', 'address', 'department', 'avatar',
            'date_joined', 'is_verified', 'is_active', 'profile',
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified', 'is_active']
    
    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj):
        return self.get_full_name(obj)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=False)
    confirmPassword = serializers.CharField(write_only=True, required=False)
    name = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(required=False, allow_blank=True)
    # Public registration must never allow a caller to choose a privileged role.
    role = serializers.ChoiceField(choices=Role.choices, read_only=True, default=Role.CUSTOMER)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'confirmPassword',
            'name', 'first_name', 'last_name', 'role', 'phone', 'address', 'department',
        ]
    
    def validate(self, attrs):
        confirm = attrs.get('password_confirm') or attrs.get('confirmPassword')
        if not confirm or attrs['password'] != confirm:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        name = attrs.get('name')
        if name and not attrs.get('first_name'):
            parts = name.split(None, 1)
            attrs['first_name'] = parts[0]
            attrs['last_name'] = parts[1] if len(parts) > 1 else ''
        if not attrs.get('username'):
            attrs['username'] = attrs['email'].split('@')[0]
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        validated_data.pop('confirmPassword', None)
        validated_data.pop('name', None)
        validated_data['role'] = Role.CUSTOMER
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user


class AdminUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=[
        (Role.CUSTOMER, 'Customer'),
        (Role.INVESTIGATOR, 'Investigator'),
        (Role.EMPLOYEE, 'Insurance Employee'),
        (Role.REPAIR, 'Repair Shop'),
    ])
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        username_base = slugify(email.split('@', 1)[0])[:150] or 'user'
        username = username_base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix_text = str(suffix)
            username = f'{username_base[:150 - len(suffix_text)]}{suffix_text}'
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **validated_data,
        )
        UserProfile.objects.create(user=user)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class RefreshTokenRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'address', 'department', 'avatar', 'profile',
        ]
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
