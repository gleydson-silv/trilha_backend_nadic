from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import Customer, Seller
from ..serializers import ProfileCompletionSerializer, normalize_serializer_errors
from ..validators import format_cnpj, format_cpf, format_phone
from .utils import (
    _customer_payload,
    _seller_payload,
    error_response,
    ok_response,
)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="5/m", method="PATCH")
def complete_profile(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = ProfileCompletionSerializer(
        data=request.data,
        context={"request": request},
        partial=True,
    )
    if serializer.is_valid():
        serializer.save()
        return ok_response(message="Perfil atualizado com sucesso.")
    return error_response(
        "Dados inválidos.", details=normalize_serializer_errors(serializer.errors)
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
def profile(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user = request.user
    if user.role == "seller":
        seller = getattr(user, "seller_profile", None)
        if not seller:
            return error_response(
                "Perfil de vendedor não encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return ok_response(data=_seller_payload(user, seller))

    if user.role == "customer":
        customer = getattr(user, "customer_profile", None)
        if not customer:
            return error_response(
                "Perfil de cliente não encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return ok_response(data=_customer_payload(user, customer))

    return error_response(
        "Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND
    )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="5/m", method="PUT")
def update_profile(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user = request.user
    data = request.data

    if user.role == "seller":
        phone_value = data.get("phone_number")
        cnpj_value = data.get("cnpj")
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cnpj_value is not None:
            cnpj_value = format_cnpj(cnpj_value)

        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.email = data.get("email", user.email)
        try:
            user.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        user.save()
        seller, _ = Seller.objects.get_or_create(user=user)
        if cnpj_value is not None:
            seller.cnpj = cnpj_value
        seller.company_name = data.get("company_name", seller.company_name)
        if phone_value is not None:
            seller.phone_number = phone_value
        try:
            seller.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        seller.save()
        return ok_response(data=_seller_payload(user, seller))

    if user.role == "customer":
        phone_value = data.get("phone_number")
        cpf_value = data.get("cpf")
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cpf_value is not None:
            cpf_value = format_cpf(cpf_value)

        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.email = data.get("email", user.email)
        try:
            user.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
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
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        customer.save()
        return ok_response(data=_customer_payload(user, customer))

    return error_response(
        "Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="5/m", method="POST")
def update_profile_partial(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user = request.user
    data = request.data

    if user.role == "seller":
        phone_value = data.get("phone_number")
        cnpj_value = data.get("cnpj")
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cnpj_value is not None:
            cnpj_value = format_cnpj(cnpj_value)

        if "first_name" in data:
            user.first_name = data.get("first_name", user.first_name)
        if "last_name" in data:
            user.last_name = data.get("last_name", user.last_name)
        if "email" in data:
            user.email = data.get("email", user.email)
        try:
            user.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        user.save()
        seller, _ = Seller.objects.get_or_create(user=user)
        if "cnpj" in data:
            seller.cnpj = cnpj_value
        if "company_name" in data:
            seller.company_name = data.get("company_name", seller.company_name)
        if "phone_number" in data:
            seller.phone_number = phone_value
        try:
            seller.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        seller.save()
        return ok_response(data=_seller_payload(user, seller))

    if user.role == "customer":
        phone_value = data.get("phone_number")
        cpf_value = data.get("cpf")
        if phone_value is not None:
            phone_value = format_phone(phone_value)
        if cpf_value is not None:
            cpf_value = format_cpf(cpf_value)

        if "first_name" in data:
            user.first_name = data.get("first_name", user.first_name)
        if "last_name" in data:
            user.last_name = data.get("last_name", user.last_name)
        if "email" in data:
            user.email = data.get("email", user.email)
        try:
            user.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        user.save()
        customer, _ = Customer.objects.get_or_create(user=user)
        if "cpf" in data:
            customer.cpf = cpf_value
        if "phone_number" in data:
            customer.phone_number = phone_value
        customer.first_name = user.first_name
        customer.last_name = user.last_name
        try:
            customer.full_clean()
        except DjangoValidationError as exc:
            return error_response(
                "Dados inválidos.",
                details=normalize_serializer_errors(exc.message_dict),
            )
        customer.save()
        return ok_response(data=_customer_payload(user, customer))

    return error_response(
        "Perfil não encontrado", status_code=status.HTTP_404_NOT_FOUND
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="5/m", method="DELETE")
def delete_account(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    request.user.delete()
    return ok_response(message="Conta deletada com sucesso")
