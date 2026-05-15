import requests
from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import Address, User
from ..validators import validate_cep
from .utils import error_response, ok_response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/m", method="GET")
def consultar_cep(request, cep):
    if getattr(request, "limited", False):
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
        message = (
            exc.messages[0] if getattr(exc, "messages", None) else "CEP inválido"
        )
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="5/m", method="POST")
def register_address(request):
    if getattr(request, "limited", False):
        return error_response(
            "Limite máximo de requisições atingido.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user = request.user
    if user.role != User.Role.CUSTOMER:
        return error_response(
            "Apenas clientes podem cadastrar endereço.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    customer = getattr(user, "customer_profile", None)
    if not customer:
        return error_response(
            "Perfil de cliente não encontrado",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    data = request.data
    address = Address.objects.create(
        customer=customer,
        zip_code=data.get("zip_code"),
        street=data.get("street"),
        number=data.get("number"),
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country"),
    )

    return ok_response(
        data={
            "zip_code": address.zip_code,
            "street": address.street,
            "number": address.number,
            "city": address.city,
            "state": address.state,
            "country": address.country,
        },
        message="Endereço registrado com sucesso",
        status_code=status.HTTP_201_CREATED,
    )
