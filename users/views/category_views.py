from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination

from ..models import Category
from ..permissions import CategoryAccessPermission
from ..serializers import CategorySerializer, normalize_serializer_errors
from .utils import error_response, ok_response


class CategoryPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [CategoryAccessPermission]
    pagination_class = CategoryPagination

    def get_paginated_response(self, data):
        return ok_response(data=super().get_paginated_response(data).data)

    @method_decorator(ratelimit(key="user", rate="60/m", method="GET"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(ratelimit(key="user", rate="10/m", method="POST"))
    def create(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return ok_response(data=serializer.data, status_code=status.HTTP_201_CREATED)
        return error_response(
            "Dados inválidos.",
            details=normalize_serializer_errors(serializer.errors),
        )

    @method_decorator(ratelimit(key="user", rate="60/m", method="GET"))
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ok_response(data=serializer.data)

    @method_decorator(ratelimit(key="user", rate="10/m", method="PUT"))
    def update(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return ok_response(data=serializer.data)
        return error_response(
            "Dados inválidos.",
            details=normalize_serializer_errors(serializer.errors),
        )

    @method_decorator(ratelimit(key="user", rate="10/m", method="PATCH"))
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @method_decorator(ratelimit(key="user", rate="10/m", method="DELETE"))
    def destroy(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return error_response(
                "Limite máximo de requisições atingido.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        instance = self.get_object()
        self.perform_destroy(instance)
        return ok_response(status_code=status.HTTP_204_NO_CONTENT)
