"""
Auth views — Login, Logout, Register, Token Refresh, Profile
"""
import binascii
import logging
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.validators import validate_email
from rest_framework import serializers, status, permissions
from rest_framework.exceptions import APIException
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """POST /api/v1/auth/login/ — Returns JWT tokens"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {'detail': 'Correo electrónico o contraseña incorrectos.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not user.is_active:
            return Response(
                {'detail': 'Esta cuenta ha sido desactivada. Contacta al administrador.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class RegisterView(APIView):
    """POST /api/v1/auth/register/ — Register new professional user"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Cuenta creada exitosamente.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — Blacklist refresh token"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Sesión cerrada exitosamente.'})
        except Exception:
            return Response({'message': 'Sesión cerrada.'})


class MeView(APIView):
    """GET/PATCH /api/v1/auth/me/ — Get or update current user profile"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not request.user.check_password(old_password):
            return Response(
                {'old_password': 'La contraseña actual es incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(new_password) < 8:
            return Response(
                {'new_password': 'La contraseña debe tener al menos 8 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({'message': 'Contraseña actualizada exitosamente.'})


class PasswordResetRequestView(APIView):
    """Send a single-use password-reset link without revealing account existence."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '')
        if not isinstance(email, str):
            email = ''
        email = email.strip()
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response(
                {'email': 'Ingresa un correo electrónico válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/reset-password.html"
                f"?uid={uid}&token={token}"
            )
            message = (
                f"Hola {user.first_name or 'usuario'},\n\n"
                "Recibimos una solicitud para cambiar la contraseña de tu cuenta PrevenIA. "
                f"Abre este enlace para crear una nueva contraseña:\n{reset_url}\n\n"
                "El enlace es de un solo uso y caduca en 24 horas. "
                "Si no solicitaste este cambio, ignora este mensaje."
            )
            try:
                sent = send_mail(
                    'Recuperar contraseña de PrevenIA',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception('No se pudo enviar el correo de recuperación de contraseña.')
                raise APIException('No se pudo enviar el correo ahora. Intenta de nuevo más tarde.')
            if sent != 1:
                logger.error('El backend de correo no confirmó el envío del mensaje de recuperación.')
                raise APIException('No se pudo enviar el correo ahora. Intenta de nuevo más tarde.')

        return Response({
            'detail': 'Si existe una cuenta activa con ese correo, recibirás un enlace para restablecer la contraseña.',
        })


class PasswordResetConfirmView(APIView):
    """Validate a reset token and replace the user's password."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']

        try:
            user_id = int(urlsafe_base64_decode(uid).decode())
            user = User.objects.get(pk=user_id, is_active=True)
        except (binascii.Error, ValueError, TypeError, UnicodeDecodeError, User.DoesNotExist):
            return Response(
                {'detail': 'El enlace de recuperación no es válido o ya expiró.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'El enlace de recuperación no es válido o ya expiró.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password, user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': list(error.messages)})

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Tu contraseña fue actualizada. Ya puedes iniciar sesión.'})


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return attrs
