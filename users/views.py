from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileCompletionSerializer,
    ProductSerializer,
    ProductDetailSerializer,
)
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .models import User, Product, OrderItem
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.password_validation import validate_password
import requests
from .models import Address
import pyotp


@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', method='POST')
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
@ratelimit(key='ip', rate='5/m', method='POST')
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


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def change_password(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response({'error': "As senhas atual e nova são obrigatórias"}, status = status.HTTP_400_BAD_REQUEST)
    
    if not user.check_password(current_password):
        return Response({'error': "Senha atual incorreta"}, status = status.HTTP_400_BAD_REQUEST)
    
    if new_password == current_password:
        return Response({'error': "A nova senha deve ser diferente da senha atual"}, status = status.HTTP_400_BAD_REQUEST)
    
    try:
        validate_password(new_password, user)
    except Exception as e:
        return Response({'error': str(e)}, status = status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()

    return Response({'message': "Senha alterada com sucesso"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='60/m', method='GET')
def profile(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    if user.role == 'seller':
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cnpj': user.cnpj,
            'company_name': user.company_name,
            'phone_number': user.phone_number,
        })
    
    if user.role == 'customer':
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cpf': user.cpf,
            'phone_number': user.phone_number,
            
        })
    
    if user.role == 'admin':
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
        })
    
    return Response({ 'error': "Perfil não encontrado"}, status = status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='PUT')
def update_profile(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    data = request.data

    if user.role == 'seller':
        user.cnpj = data.get('cnpj', user.cnpj)
        user.company_name = data.get('company_name', user.company_name)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cnpj': user.cnpj,
            'company_name': user.company_name,
            'phone_number': user.phone_number,
        })
    if user.role == 'customer':
        user.phone_number = data.get('phone_number', user.phone_number)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cpf': user.cpf,
            'phone_number': user.phone_number,
        })
    if user.role == 'admin':
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
        })



    return Response({
        'error': "Perfil não encontrado"
    }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def update_profile_partial(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    data = request.data

    if user.role == 'seller':
        user.cnpj = data.get('cnpj', user.cnpj)
        user.company_name = data.get('company_name', user.company_name)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cnpj': user.cnpj,
            'company_name': user.company_name,
            'phone_number': user.phone_number,
        })
    if user.role == 'customer':
        user.phone_number = data.get('phone_number', user.phone_number)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
            'cpf': user.cpf,
            'phone_number': user.phone_number,
        })
    if user.role == 'admin':
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        return Response({
            'name': user.first_name + " " + user.last_name,
            'email': user.email,
        })



    return Response({
        'error': "Perfil não encontrado"
    }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='60/m', method='GET')
def consultar_cep(request, cep):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return Response(
                {"error": "Erro ao consultar serviço de CEP"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        data = response.json()

        
        if "erro" in data:
            return Response(
                {"error": "CEP inválido ou não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        Address.zip_code = cep
        Address.save()
        return Response(data, status=status.HTTP_200_OK)

    except requests.exceptions.Timeout:
        return Response(
            {"error": "Timeout ao consultar CEP"},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )

    except requests.exceptions.RequestException:
        return Response(
            {"error": "Erro de conexão com o serviço de CEP"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def register_address(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    data = request.data

    address = Address.objects.create(
        user=user,
        zip_code=data.get('zip_code'),
        street=data.get('street'),
        number=data.get('number'),
        complement=data.get('complement'),
        neighborhood=data.get('neighborhood'),
        city=data.get('city'),
        state=data.get('state')
    )

    return Response({
        'message': "Endereço registrado com sucesso",
        'address': {
            'zip_code': address.zip_code,
            'street': address.street,
            'number': address.number,
            'complement': address.complement,
            'neighborhood': address.neighborhood,
            'city': address.city,
            'state': address.state
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='DELETE')
def delete_account(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user
    user.delete()
    return Response({"message": "Conta deletada com sucesso"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
def verify_2fa(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    email = request.data.get("email")
    code = request.data.get("code")

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)

    totp = pyotp.TOTP(user.two_factor_secret)

    if not totp.verify(code):
        return Response({"error": "Código inválido"}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    })


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def enable_2fa(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user

    if user.two_factor_enabled:
        return Response({"error": "2FA já está habilitado"}, status=status.HTTP_400_BAD_REQUEST)
    
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    user.two_factor_enabled = True
    user.save()

    return Response({"message": "2FA habilitado com sucesso", "secret": secret}, status=status.HTTP_200_OK)


@api_view(['POST'])
@ratelimit(key='user', rate='5/m', method='POST')
@permission_classes([IsAuthenticated])
def disable_2fa(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = request.user

    if not user.two_factor_enabled:
        return Response({"error": "2FA já está desabilitado"}, status=status.HTTP_400_BAD_REQUEST)
    
    user.two_factor_secret = ""
    user.two_factor_enabled = False
    user.save()
    return Response({"message": "2FA desabilitado com sucesso"}, status=status.HTTP_200_OK)


def _is_seller(user):
    return user.is_authenticated and user.role == User.Role.SELLER


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="POST")
def products_list_create(request):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if request.method == "GET":
        if _is_seller(request.user):
            queryset = Product.objects.filter(seller=request.user.seller_profile)
        else:
            queryset = Product.objects.all()
        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if not _is_seller(request.user):
        return Response(
            {"error": "Apenas vendedores podem cadastrar produtos."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = ProductSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="PUT")
@ratelimit(key="user", rate="10/m", method="PATCH")
@ratelimit(key="user", rate="10/m", method="DELETE")
def product_detail_update_delete(request, product_id):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Produto não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if not _is_seller(request.user):
        return Response(
            {"error": "Apenas vendedores podem editar/remover produtos."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if product.seller.user_id != request.user.id:
        return Response(
            {"error": "Você não tem permissão para alterar este produto."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
        context={"request": request},
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
def product_details_with_stock(request, product_id):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Produto não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductDetailSerializer(product)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="30/m", method="GET")
def company_revenue(request):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Limite máximo de requisições atingido."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if not _is_seller(request.user):
        return Response(
            {"error": "Apenas o dono da empresa pode acessar este endpoint."},
            status=status.HTTP_403_FORBIDDEN,
        )

    total = OrderItem.objects.filter(product__seller=request.user.seller_profile).aggregate(
        total_revenue=Sum(
            ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField())
        )
    )["total_revenue"]

    return Response(
        {"total_revenue": total or 0},
        status=status.HTTP_200_OK,
    )
