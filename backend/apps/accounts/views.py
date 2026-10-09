from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import secrets
import logging

from .models import User, UserProfile
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UserUpdateSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    
    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        elif self.action == 'login':
            return UserLoginSerializer
        elif self.action == 'logout':
            return serializers.Serializer
        elif self.action == 'refresh':
            return serializers.Serializer
        elif self.action == 'me':
            return UserSerializer
        elif self.action == 'update_profile':
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        elif self.action == 'forgot_password':
            return PasswordResetRequestSerializer
        elif self.action == 'reset_password':
            return PasswordResetConfirmSerializer
        return UserSerializer
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 401, 'message': 'Invalid credentials'}
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({
                'success': False,
                'error': {'code': 401, 'message': 'Invalid credentials'}
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': {'code': 403, 'message': 'Account is disabled'}
            }, status=status.HTTP_403_FORBIDDEN)
        
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login_ip'])
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        
        return Response({'success': True, 'message': 'Logged out successfully'})
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Refresh token required'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            access_token = token.access_token
            return Response({
                'success': True,
                'data': {'access': str(access_token)}
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {'code': 401, 'message': 'Invalid refresh token'}
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Current password is incorrect'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'success': True, 'message': 'Password changed successfully'})
    
    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            reset_token = secrets.token_urlsafe(32)
            user.password_reset_token = reset_token
            user.password_reset_token_created = timezone.now()
            user.save(update_fields=['password_reset_token', 'password_reset_token_created'])
            
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {reset_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'message': 'If the email exists, a password reset link has been sent.'
        })
    
    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        try:
            user = User.objects.get(password_reset_token=token)
            if user.password_reset_token_created < timezone.now() - timezone.timedelta(hours=1):
                return Response({
                    'success': False,
                    'error': {'code': 400, 'message': 'Reset token has expired'}
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Invalid reset token'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['password'])
        user.password_reset_token = None
        user.password_reset_token_created = None
        user.save()
        
        return Response({'success': True, 'message': 'Password reset successfully'})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response({
                'success': True,
                'data': response.data
            })
        return Response({
            'success': False,
            'error': {'code': response.status_code, 'message': 'Token refresh failed', 'details': response.data}
        }, status=response.status_code)