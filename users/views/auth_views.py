from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileCompletionSerializer,
    ProductSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    normalize_serializer_errors,
    CheckoutSerializer,
    OrderSerializer,
)
from django.db import transaction
from rest_framework import viewsets
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate, login as django_login
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from ..models import User, Product, OrderItem, Category, Seller, Customer, Order, Payment
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal, InvalidOperation
from ..permissions import IsSeller, ProductAccessPermission, CategoryAccessPermission
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import requests
from ..models import Address
import pyotp
from ..validators import format_phone, format_cpf, format_cnpj, validate_cep
from .utils import ok_response, error_response, _is_seller, _seller_payload, _customer_payload

class RegisterView(APIView):
    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST"))
    def post(self, request):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return ok_response(
                data={"id": user.id, "email": user.email},
                message="Usuário registrado com sucesso!",
                status_code=status.HTTP_201_CREATED,
            )
        return error_response(
            "Erro ao registrar usuário.",
            details=normalize_serializer_errors(serializer.errors),
        )


class LoginView(APIView):
    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST"))
    def post(self, request):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)

        if user:
            # Login do Django para suporte a sessões
            django_login(request, user, backend="allauth.account.auth_backends.AuthenticationBackend")

            # Geração de tokens JWT
            refresh = RefreshToken.for_user(user)
            return ok_response(
                data={
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role,
                        "two_factor_enabled": user.two_factor_enabled,
                    },
                },
                message="Login realizado com sucesso!",
            )

        return error_response(
            "Credenciais inválidas.", status_code=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def logout(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return ok_response(
            message="Logout realizado com sucesso.",
            status_code=status.HTTP_205_RESET_CONTENT,
        )
    except Exception as e:
        return error_response("Token inválido ou já expirado.")
    
token_generator = PasswordResetTokenGenerator()

@api_view(["POST"])
@ratelimit(key='user', rate = '5/m', method='POST')
def forgot_password(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    email = request.data.get("email")
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return error_response("Usuário não encontrado", status_code=status.HTTP_404_NOT_FOUND)

    token = token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    reset_link = f"http://localhost:3000/reset-password/{uid}/{token}/"

    send_mail(
        "Redefinir senha",
        f"Clique no link para redefinir sua senha: {reset_link}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

    return ok_response(message="Email de recuperação enviado")


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def reset_password(request,uidb64, token):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk = uid)
    except (User.DoesNotExist, ValueError, TypeError):
        return error_response("Usuario não encontrado", status_code=status.HTTP_404_NOT_FOUND)
    
    if not token_generator.check_token(user, token):
        return error_response("Token invalido ou expirado")
    
    new_password = request.data.get('password')
    if not new_password:
        return error_response("A nova senha é obrigatoria")
    
    user.set_password(new_password)
    user.save()
    
    return ok_response(message="Senha alterada com sucesso")


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def change_password(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return error_response("As senhas atual e nova são obrigatórias")
    
    if not user.check_password(current_password):
        return error_response("Senha atual incorreta")
    
    if new_password == current_password:
        return error_response("A nova senha deve ser diferente da senha atual")
    
    try:
        validate_password(new_password, user)
    except Exception as e:
        return error_response(str(e))
    
    user.set_password(new_password)
    user.save()

    return ok_response(message="Senha alterada com sucesso")

@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def verify_2fa(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    email = request.data.get("email")
    code = request.data.get("code")

    user = User.objects.filter(email=email).first()
    if not user:
        return error_response("Usuário não encontrado", status_code=status.HTTP_404_NOT_FOUND)

    totp = pyotp.TOTP(user.two_factor_secret)

    if not totp.verify(code):
        return error_response("Código inválido")

    refresh = RefreshToken.for_user(user)

    return ok_response(
        data={
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def enable_2fa(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user

    if user.two_factor_enabled:
        return error_response("2FA já está habilitado")
    
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    user.two_factor_enabled = True
    user.save()

    return ok_response(
        data={"secret": secret},
        message="2FA habilitado com sucesso",
    )


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def disable_2fa(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user

    if not user.two_factor_enabled:
        return error_response("2FA já está desabilitado")
    
    user.two_factor_secret = ""
    user.two_factor_enabled = False
    user.save()
    return ok_response(message="2FA desabilitado com sucesso")
