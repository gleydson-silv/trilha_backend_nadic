from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.decorators import action
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

class ProductPagination(PageNumberPagination):
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

    @action(detail=True, methods=['delete', 'post'], url_path='delete')
    def delete_product(self, request, pk=None):
        """
        Endpoint explícito para exclusão de produto.
        Acessível via DELETE ou POST em /products/<id>/delete/
        """
        product = self.get_object()
        product.delete()
        return Response({
            "success": True, 
            "message": "Produto excluído com sucesso do seu catálogo."
        }, status=status.HTTP_200_OK)


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

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                "Dados de checkout inválidos.", 
                data=normalize_serializer_errors(serializer.errors),
                status_code=status.HTTP_400_BAD_REQUEST
            )

        items_data = serializer.validated_data.get('items')
        user = request.user
        
        # Garantir que temos um perfil de cliente
        customer, _ = Customer.objects.get_or_create(user=user)

        total_amount = Decimal('0.00')
        order_items = []

        for item in items_data:
            product_id = item.get('product_id')
            quantity = item.get('quantity')

            try:
                # Select for update para evitar concorrência no estoque
                product = Product.objects.select_for_update().get(pk=product_id)
            except Product.DoesNotExist:
                return error_response(f"Produto ID {product_id} não encontrado.")

            if product.quantity_in_stock < quantity:
                return error_response(
                    f"Estoque insuficiente para {product.name}. Disponível: {product.quantity_in_stock}"
                )

            # Atualiza o estoque (Ponto 2 do plano)
            product.quantity_in_stock -= quantity
            product.save()

            unit_price = product.price
            total_amount += unit_price * quantity

            order_items.append(OrderItem(
                product=product,
                quantity=quantity,
                unit_price=unit_price
            ))

        # Cria o pedido
        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            state='pending'
        )

        # Associa os itens ao pedido
        for item in order_items:
            item.order = order
            item.save()

        return ok_response(
            message="Pedido realizado com sucesso!",
            data={"order_id": order.id, "total": str(total_amount)}
        )
