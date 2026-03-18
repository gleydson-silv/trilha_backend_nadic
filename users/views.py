from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate

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



