from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

cpf_format_validator = RegexValidator(
    regex=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$",
    message="CPF deve estar no formato XXX.XXX.XXX-XX",
)

cnpj_format_validator = RegexValidator(
    regex=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$",
    message="CNPJ deve estar no formato XX.XXX.XXX/XXXX-XX",
)

phone_format_validator = RegexValidator(
    regex=r"^\d{2}-\d{9}$",
    message="Telefone deve estar no formato XX-XXXXXXXXX",
)


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def format_phone(value: str) -> str:
    digits = _only_digits(value or "")
    if len(digits) != 11:
        return value
    return f"{digits[:2]}-{digits[2:]}"


def format_cpf(value: str) -> str:
    digits = _only_digits(value or "")
    if len(digits) != 11:
        return value
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def format_cnpj(value: str) -> str:
    digits = _only_digits(value or "")
    if len(digits) != 14:
        return value
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    

def validate_cep(value: str) -> None:
    raw = (value or "").strip()
    if raw and not all(ch.isdigit() or ch == "-" for ch in raw):
        raise ValidationError("CEP deve conter apenas números e hífen")

    cep = _only_digits(raw)
    if len(cep) != 8:
        raise ValidationError("CEP deve conter 8 dígitos")
    if cep == cep[0] * 8:
        raise ValidationError("CEP inválido")
