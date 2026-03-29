from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileCompletionSerializer,
    ProductSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    normalize_serializer_errors,
)
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .models import User, Product, OrderItem, Category, Seller, Customer
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal, InvalidOperation
from .permissions import IsSeller, ProductAccessPermission, CategoryAccessPermission
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import requests
from .models import Address
import pyotp


def ok_response(data=None, message=None, status_code=status.HTTP_200_OK):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)


def error_response(error, status_code=status.HTTP_400_BAD_REQUEST, details=None):
    payload = {"success": False, "error": error}
    if details is not None:
        payload["details"] = details
    return Response(payload, status=status_code)


@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', method='POST')
def register(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    serializer = RegisterSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
        return ok_response(
            message="Usuário registrado com sucesso!",
            status_code=status.HTTP_201_CREATED,
        )
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))


@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', method='POST')
def login(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    data = request.data
    email = data.get('email')
    password = data.get('password')
    
    user = authenticate(email = email, password=password)
    
    if not user:
        return error_response("Credenciais inválidas", status_code=status.HTTP_401_UNAUTHORIZED)
    
    if user.two_factor_enabled:
        return ok_response(
            data={"2fa_required": True},
            message="Informe o codigo de verificação",
        )
    
    refresh = RefreshToken.for_user(user)
    
    return ok_response(
        data={
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='PATCH')
def complete_profile(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = ProfileCompletionSerializer(
        data=request.data,
        context={"request": request},
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return ok_response(message="Perfil atualizado com sucesso.")
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='60/m', method='GET')
def profile(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    if user.role == 'seller':
        seller = getattr(user, "seller_profile", None)
        if not seller:
            return error_response("Perfil de vendedor não encontrado", status_code=status.HTTP_404_NOT_FOUND)
        return ok_response(data=_seller_payload(user, seller))
    
    if user.role == 'customer':
        customer = getattr(user, "customer_profile", None)
        if not customer:
            return error_response("Perfil de cliente não encontrado", status_code=status.HTTP_404_NOT_FOUND)
        return ok_response(data=_customer_payload(user, customer))

    return error_response("Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='PUT')
def update_profile(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    data = request.data

    if user.role == 'seller':
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        seller, _ = Seller.objects.get_or_create(user=user)
        seller.cnpj = data.get('cnpj', seller.cnpj)
        seller.company_name = data.get('company_name', seller.company_name)
        seller.phone_number = data.get('phone_number', seller.phone_number)
        try:
            seller.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        seller.save()
        return ok_response(data=_seller_payload(user, seller))
    if user.role == 'customer':
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        customer, _ = Customer.objects.get_or_create(user=user)
        customer.cpf = data.get('cpf', customer.cpf)
        customer.phone_number = data.get('phone_number', customer.phone_number)
        customer.first_name = user.first_name
        customer.last_name = user.last_name
        try:
            customer.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        customer.save()
        return ok_response(data=_customer_payload(user, customer))
    return error_response("Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def update_profile_partial(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    data = request.data

    if user.role == 'seller':
        if 'first_name' in data:
            user.first_name = data.get('first_name', user.first_name)
        if 'last_name' in data:
            user.last_name  = data.get('last_name', user.last_name)
        if 'email' in data:
            user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        seller, _ = Seller.objects.get_or_create(user=user)
        if 'cnpj' in data:
            seller.cnpj = data.get('cnpj', seller.cnpj)
        if 'company_name' in data:
            seller.company_name = data.get('company_name', seller.company_name)
        if 'phone_number' in data:
            seller.phone_number = data.get('phone_number', seller.phone_number)
        try:
            seller.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        seller.save()
        return ok_response(data=_seller_payload(user, seller))
    if user.role == 'customer':
        if 'first_name' in data:
            user.first_name = data.get('first_name', user.first_name)
        if 'last_name' in data:
            user.last_name  = data.get('last_name', user.last_name)
        if 'email' in data:
            user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        customer, _ = Customer.objects.get_or_create(user=user)
        if 'cpf' in data:
            customer.cpf = data.get('cpf', customer.cpf)
        if 'phone_number' in data:
            customer.phone_number = data.get('phone_number', customer.phone_number)
        customer.first_name = user.first_name
        customer.last_name = user.last_name
        try:
            customer.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        customer.save()
        return ok_response(data=_customer_payload(user, customer))
    return error_response("Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='60/m', method='GET')
def consultar_cep(request, cep):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return error_response(
                "Erro ao consultar serviço de CEP",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        data = response.json()

        
        if "erro" in data:
            return error_response(
                "CEP inválido ou não encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        Address.zip_code = cep
        Address.save()
        return ok_response(data=data)

    except requests.exceptions.Timeout:
        return error_response(
            "Timeout ao consultar CEP",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    except requests.exceptions.RequestException:
        return error_response(
            "Erro de conexão com o serviço de CEP",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='POST')
def register_address(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    if user.role != User.Role.CUSTOMER:
        return error_response("Apenas clientes podem cadastrar endereço.", status_code=status.HTTP_403_FORBIDDEN)
    customer = getattr(user, "customer_profile", None)
    if not customer:
        return error_response("Perfil de cliente não encontrado", status_code=status.HTTP_404_NOT_FOUND)

    data = request.data
    address = Address.objects.create(
        customer=customer,
        zip_code=data.get('zip_code'),
        street=data.get('street'),
        number=data.get('number'),
        city=data.get('city'),
        state=data.get('state'),
        country=data.get('country'),
    )

    return ok_response(
        data={
            'zip_code': address.zip_code,
            'street': address.street,
            'number': address.number,
            'city': address.city,
            'state': address.state,
            'country': address.country,
        },
        message="Endereço registrado com sucesso",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/m', method='DELETE')
def delete_account(request):
    if getattr(request, 'limited', False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    user = request.user
    user.delete()
    return ok_response(message="Conta deletada com sucesso")


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


def _is_seller(user):
    return user.is_authenticated and user.role == User.Role.SELLER


def _seller_payload(user, seller):
    return {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "cnpj": seller.cnpj,
        "company_name": seller.company_name,
        "phone_number": seller.phone_number,
    }


def _customer_payload(user, customer):
    return {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "cpf": customer.cpf,
        "phone_number": customer.phone_number,
    }


class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoryPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "POST"])
@permission_classes([ProductAccessPermission])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="POST")
def products_list_create(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if request.method == "GET":
        if _is_seller(request.user):
            queryset = Product.objects.filter(seller=request.user.seller_profile)
        else:
            queryset = Product.objects.all()

        category_id = request.query_params.get("category")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        in_stock = request.query_params.get("in_stock")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except InvalidOperation:
                return error_response("min_price inválido.")

        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except InvalidOperation:
                return error_response("max_price inválido.")

        if in_stock is not None:
            if in_stock.lower() in ("1", "true", "yes"):
                queryset = queryset.filter(quantity_in_stock__gt=0)
            elif in_stock.lower() in ("0", "false", "no"):
                queryset = queryset.filter(quantity_in_stock=0)
            else:
                return error_response("in_stock inválido. Use true/false.")

        paginator = ProductPagination()
        page = paginator.paginate_queryset(queryset.order_by("-created_at"), request)
        serializer = ProductSerializer(page, many=True)
        paginated = paginator.get_paginated_response(serializer.data).data
        return ok_response(data=paginated)

    if not _is_seller(request.user):
        return error_response(
            "Apenas vendedores podem cadastrar produtos.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    serializer = ProductSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return ok_response(data=serializer.data, status_code=status.HTTP_201_CREATED)
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([ProductAccessPermission])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="PUT")
@ratelimit(key="user", rate="10/m", method="PATCH")
@ratelimit(key="user", rate="10/m", method="DELETE")
def product_detail_update_delete(request, product_id):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return error_response("Produto não encontrado.", status_code=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductDetailSerializer(product)
        return ok_response(data=serializer.data)

    if not _is_seller(request.user):
        return error_response(
            "Apenas vendedores podem editar/remover produtos.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if product.seller.user_id != request.user.id:
        return error_response(
            "Você não tem permissão para alterar este produto.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        product.delete()
        return ok_response(status_code=status.HTTP_204_NO_CONTENT)

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
        context={"request": request},
    )
    if serializer.is_valid():
        serializer.save()
        return ok_response(data=serializer.data)
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
def product_details_with_stock(request, product_id):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return error_response("Produto não encontrado.", status_code=status.HTTP_404_NOT_FOUND)

    serializer = ProductDetailSerializer(product)
    return ok_response(data=serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSeller])
@ratelimit(key="user", rate="30/m", method="GET")
def company_revenue(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    total = OrderItem.objects.filter(product__seller=request.user.seller_profile).aggregate(
        total_revenue=Sum(
            ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField())
        )
    )["total_revenue"]

    return ok_response(data={"total_revenue": total or 0})


@api_view(["GET", "POST"])
@permission_classes([CategoryAccessPermission])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="POST")
def categories_list_create(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if request.method == "GET":
        queryset = Category.objects.all().order_by("name")
        paginator = CategoryPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CategorySerializer(page, many=True)
        paginated = paginator.get_paginated_response(serializer.data).data
        return ok_response(data=paginated)

    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return ok_response(data=serializer.data, status_code=status.HTTP_201_CREATED)
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([CategoryAccessPermission])
@ratelimit(key="user", rate="60/m", method="GET")
@ratelimit(key="user", rate="10/m", method="PUT")
@ratelimit(key="user", rate="10/m", method="PATCH")
@ratelimit(key="user", rate="10/m", method="DELETE")
def category_detail_update_delete(request, category_id):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return error_response("Categoria não encontrada.", status_code=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = CategorySerializer(category)
        return ok_response(data=serializer.data)

    if request.method == "DELETE":
        category.delete()
        return ok_response(status_code=status.HTTP_204_NO_CONTENT)

    serializer = CategorySerializer(
        category,
        data=request.data,
        partial=(request.method == "PATCH"),
    )
    if serializer.is_valid():
        serializer.save()
        return ok_response(data=serializer.data)
    return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))
