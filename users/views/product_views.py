from decimal import Decimal, InvalidOperation

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Product
from ..permissions import ProductAccessPermission
from ..serializers import ProductDetailSerializer, ProductSerializer
from .utils import _is_seller, error_response, ok_response


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
        if user.is_authenticated and _is_seller(user):
            queryset = Product.objects.filter(seller=user.seller_profile)
        else:
            queryset = Product.objects.all()

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
        serializer.save(seller=self.request.user.seller_profile)

    @action(detail=True, methods=["delete", "post"], url_path="delete")
    def delete_product(self, request, pk=None):
        product = self.get_object()
        product.delete()
        return Response(
            {
                "success": True,
                "message": "Produto excluído com sucesso do seu catálogo.",
            },
            status=status.HTTP_200_OK,
        )


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
        return error_response(
            "Produto não encontrado.", status_code=status.HTTP_404_NOT_FOUND
        )

    serializer = ProductDetailSerializer(product)
    return ok_response(data=serializer.data)
