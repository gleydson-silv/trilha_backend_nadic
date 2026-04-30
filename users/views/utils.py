from rest_framework.response import Response
from rest_framework import status
from ..models import User

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
