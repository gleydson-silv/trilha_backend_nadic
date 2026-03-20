from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import RegisterSerializer, LoginSerializer, ProfileCompletionSerializer
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes

@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def register(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    serializer = RegisterSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"messsage": "Usuário registrado com sucesso! " },status = status.HTTP_201_CREATED)
    return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def login(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    data = request.data
    email = data.get('email')
    password = data.get('password')
    
    user = authenticate(email = email, password=password)
    
    if not user:
        return Response({"error": "Credenciais inválidas"}, status = status.HTTP_401_UNAUTHORIZED)
    
    if user.two_factor_enabled:
        return Response({
            "2fa_required": True,
            "message": "Informe o codigo de verificação"}, status = status.HTTP_200_OK)
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
        })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='PATCH')
def complete_profile(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    serializer = ProfileCompletionSerializer(
        data=request.data,
        context={"request": request},
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Perfil atualizado com sucesso."},
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def logout(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Logout realizado com sucesso."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response({"error": "Token inválido ou já expirado."}, status=status.HTTP_400_BAD_REQUEST)
    
token_generator = PasswordResetTokenGenerator()


@api_view(["POST"])
@ratelimit(key='user', rate = '5/m', method='POST')
def forgot_password(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    email = request.data.get("email")
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)

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

    return Response({"message": "Email de recuperação enviado"})


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def reset_password(request,uidb64, token):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk = uid)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({'error': "Usuario não encontrado"}, status = status.HTTP_404_NOT_FOUND)
    
    if not token_generator.check_token(user, token):
        return Response({'error': "Token invalido ou expirado"}, status = status.HTTP_400_BAD_REQUEST)
    
    new_password = request.data.get('password')
    if not new_password:
        return Response({'error': "A nova senha é obrigatoria"}, status = status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': "Senha alterada com sucesso"}, status=status.HTTP_200_OK)