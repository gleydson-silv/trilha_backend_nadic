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

class CompanyRevenueView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    @method_decorator(ratelimit(key="user", rate="30/m", method="GET"))
    def get(self, request):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        total = OrderItem.objects.filter(
            product__seller=request.user.seller_profile
        ).aggregate(
            total_revenue=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"), output_field=DecimalField()
                )
            )
        )[
            "total_revenue"
        ]

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

