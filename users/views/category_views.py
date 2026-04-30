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
        return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))

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
        return error_response("Dados inválidos.", details=normalize_serializer_errors(serializer.errors))

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
