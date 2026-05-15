from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import Customer, Order, OrderItem, Payment, Product
from ..permissions import IsSeller
from ..serializers import (
    CheckoutSerializer,
    OrderSerializer,
    normalize_serializer_errors,
)
from .utils import error_response, ok_response


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
        )["total_revenue"]

        return ok_response(data={"total_revenue": total or 0})


class CheckoutView(APIView):
    """Checkout único: pedido, itens, baixa de estoque e pagamento."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    @method_decorator(ratelimit(key="user", rate="10/m", method="POST"))
    def post(self, request):
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
                for item in items_data:
                    try:
                        product = Product.objects.select_for_update().get(
                            pk=item["product_id"]
                        )
                    except Product.DoesNotExist:
                        raise ValueError(
                            f"Produto ID {item['product_id']} não encontrado."
                        )

                    if product.quantity_in_stock < item["quantity"]:
                        raise ValueError(
                            f"Estoque insuficiente para o produto: {product.name}."
                        )

                    unit_price = product.price
                    total_amount += unit_price * item["quantity"]
                    prepared_items.append(
                        {
                            "product": product,
                            "quantity": item["quantity"],
                            "unit_price": unit_price,
                        }
                    )

                order = Order.objects.create(
                    customer=customer,
                    total_amount=total_amount,
                    state="pending",
                )

                for item in prepared_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                    )
                    item["product"].quantity_in_stock -= item["quantity"]
                    item["product"].save()

                Payment.objects.create(
                    order=order,
                    amount=total_amount,
                    payment_method=payment_method,
                )

            return ok_response(
                data=OrderSerializer(order).data,
                message="Pedido realizado com sucesso!",
                status_code=status.HTTP_201_CREATED,
            )

        except ValueError as exc:
            return error_response(str(exc))
        except Exception:
            return error_response("Erro interno ao processar o pedido.")
