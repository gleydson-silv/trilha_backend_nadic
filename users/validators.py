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


def validate_cpf(value: str) -> None:
    digits = _only_digits(value or "")
    if len(digits) != 11:
        raise ValidationError("CPF inválido")
    if digits == digits[0] * 11:
        raise ValidationError("CPF inválido")

    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    check_1 = (total * 10) % 11
    check_1 = 0 if check_1 == 10 else check_1
    if check_1 != int(digits[9]):
        raise ValidationError("CPF inválido")

    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    check_2 = (total * 10) % 11
    check_2 = 0 if check_2 == 10 else check_2
    if check_2 != int(digits[10]):
        raise ValidationError("CPF inválido")


def validate_cnpj(value: str) -> None:
    digits = _only_digits(value or "")
    if len(digits) != 14:
        raise ValidationError("CNPJ inválido")
    if digits == digits[0] * 14:
        raise ValidationError("CNPJ inválido")

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_1[i] for i in range(12))
    mod = total % 11
    check_1 = 0 if mod < 2 else 11 - mod
    if check_1 != int(digits[12]):
        raise ValidationError("CNPJ inválido")

    weights_2 = [6] + weights_1
    total = sum(int(digits[i]) * weights_2[i] for i in range(13))
    mod = total % 11
    check_2 = 0 if mod < 2 else 11 - mod
    if check_2 != int(digits[13]):
        raise ValidationError("CNPJ inválido")
    

def validate_cep(value: str) -> None:
    raw = (value or "").strip()
    if raw and not all(ch.isdigit() or ch == "-" for ch in raw):
        raise ValidationError("CEP deve conter apenas números e hífen")

    cep = _only_digits(raw)
    if len(cep) != 8:
        raise ValidationError("CEP deve conter 8 dígitos")
    if cep == cep[0] * 8:
        raise ValidationError("CEP inválido")
