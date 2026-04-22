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
from .models import User, Product, OrderItem, Category, Seller, Customer, Order, Payment
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
from .validators import format_phone, format_cpf, format_cnpj, validate_cep


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

    django_login(request, user)
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
        phone_value = data.get('phone_number')
        cnpj_value = data.get('cnpj')
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cnpj_value is not None:
            cnpj_value = format_cnpj(cnpj_value)

        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        seller, _ = Seller.objects.get_or_create(user=user)
        if cnpj_value is not None:
            seller.cnpj = cnpj_value
        seller.company_name = data.get('company_name', seller.company_name)
        if phone_value is not None:
            seller.phone_number = phone_value
        try:
            seller.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        seller.save()
        return ok_response(data=_seller_payload(user, seller))
    if user.role == 'customer':
        phone_value = data.get('phone_number')
        cpf_value = data.get('cpf')
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cpf_value is not None:
            cpf_value = format_cpf(cpf_value)

        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        user.save()
        customer, _ = Customer.objects.get_or_create(user=user)
        if cpf_value is not None:
            customer.cpf = cpf_value
        if phone_value is not None:
            customer.phone_number = phone_value
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
        phone_value = data.get('phone_number')
        cnpj_value = data.get('cnpj')
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cnpj_value is not None:
            cnpj_value = format_cnpj(cnpj_value)

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
            seller.cnpj = cnpj_value
        if 'company_name' in data:
            seller.company_name = data.get('company_name', seller.company_name)
        if 'phone_number' in data:
            seller.phone_number = phone_value
        try:
            seller.full_clean()
        except DjangoValidationError as e:
            return error_response("Dados inválidos.", details=normalize_serializer_errors(e.message_dict))
        seller.save()
        return ok_response(data=_seller_payload(user, seller))
    if user.role == 'customer':
        phone_value = data.get('phone_number')
        cpf_value = data.get('cpf')
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cpf_value is not None:
            cpf_value = format_cpf(cpf_value)

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
            customer.cpf = cpf_value
        if 'phone_number' in data:
            customer.phone_number = phone_value
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
        validate_cep(cep)
        cep_digits = "".join(ch for ch in cep if ch.isdigit())
        url = f"https://viacep.com.br/ws/{cep_digits}/json/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("erro"):
            return error_response("CEP inválido")

        return ok_response(data=data)

    except DjangoValidationError as exc:
        message = exc.messages[0] if getattr(exc, "messages", None) else "CEP inválido"
        return error_response(message)

    except requests.exceptions.RequestException:
        return error_response(
            "Erro ao consultar o serviço de CEP",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except Exception:
        return error_response(
            "Erro interno ao consultar CEP.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [ProductAccessPermission]
    pagination_class = ProductPagination

    def get_queryset(self):
        user = self.request.user
        # Se for vendedor, filtra apenas os produtos dele
        if user.is_authenticated and _is_seller(user):
            queryset = Product.objects.filter(seller=user.seller_profile)
        else:
            queryset = Product.objects.all()

        # Reaproveitando sua lógica de filtros por query params
        category_id = self.request.query_params.get("category")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        in_stock = self.request.query_params.get("in_stock")

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (InvalidOperation, TypeError):
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (InvalidOperation, TypeError):
                pass

        if in_stock is not None:
            if in_stock.lower() in ("1", "true", "yes"):
                queryset = queryset.filter(quantity_in_stock__gt=0)
            elif in_stock.lower() in ("0", "false", "no"):
                queryset = queryset.filter(quantity_in_stock=0)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        # Associa automaticamente o vendedor logado ao produto
        serializer.save(seller=self.request.user.seller_profile)


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="10/m", method="POST")
def checkout(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
        return error_response(
            "Apenas clientes com perfil completo podem realizar pedidos.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    serializer = CheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            "Dados de checkout inválidos.",
            details=normalize_serializer_errors(serializer.errors),
        )

    items_data = serializer.validated_data["items"]
    payment_method = serializer.validated_data["payment_method"]

    total_amount = Decimal("0.00")
    prepared_items = []

    try:
        with transaction.atomic():
            # 2. Validar estoque e calcular preços (usando select_for_update para evitar race conditions)
            for item in items_data:
                try:
                    product = Product.objects.select_for_update().get(pk=item["product_id"])
                except Product.DoesNotExist:
                    raise ValueError(f"Produto ID {item['product_id']} não encontrado.")

                if product.quantity_in_stock < item["quantity"]:
                    raise ValueError(f"Estoque insuficiente para o produto: {product.name}.")

                unit_price = product.price
                item_total = unit_price * item["quantity"]
                total_amount += item_total

                prepared_items.append(
                    {
                        "product": product,
                        "quantity": item["quantity"],
                        "unit_price": unit_price,
                    }
                )

            # 3. Criar o Pedido
            order = Order.objects.create(
                customer=customer, total_amount=total_amount, state="pending"
            )

            # 4. Criar Itens do Pedido e Atualizar Estoque
            for item in prepared_items:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )
                # Baixar estoque
                item["product"].quantity_in_stock -= item["quantity"]
                item["product"].save()

            # 5. Registrar Pagamento
            Payment.objects.create(
                order=order, amount=total_amount, payment_method=payment_method
            )

            return ok_response(
                data=OrderSerializer(order).data,
                message="Pedido realizado com sucesso!",
                status_code=status.HTTP_201_CREATED,
            )

    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response("Erro interno ao processar o pedido.", details=str(e))


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
