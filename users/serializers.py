from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.settings import api_settings
from .models import User, Customer, Seller, Product, Category


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'role',
        ]

        extra_kwargs = {
            'password': {'write_only': True}  
        }

    def create(self, validated_data):
        password = validated_data.pop("password")

        email = validated_data.get("email")
        if email:
            validated_data["email"] = User.objects.normalize_email(email)
        user = User(**validated_data)
        user.set_password(password)
        try:
            user.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        user.save()
        return user

    def validate(self, attrs):
        return attrs
        

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ProfileCompletionSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    cpf = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    cnpj = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context["request"].user
        role = user.role

        if role == User.Role.CUSTOMER:
            customer = Customer.objects.filter(user=user).first()
            cpf = attrs.get("cpf")
            if cpf:
                qs = Customer.objects.exclude(user=user).filter(cpf=cpf)
                if qs.exists():
                    raise serializers.ValidationError({"cpf": "CPF já está em uso."})
            required = ["first_name", "last_name", "cpf", "phone_number"]
            missing = []
            for field in required:
                if field in attrs and attrs.get(field):
                    continue
                current = None
                if field in ("first_name", "last_name"):
                    current = getattr(user, field, None)
                elif customer:
                    current = getattr(customer, field, None)
                if not current:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError(
                    f"Para cliente, informe: {', '.join(missing)}."
                )

        if role == User.Role.SELLER:
            seller = Seller.objects.filter(user=user).first()
            cnpj = attrs.get("cnpj")
            if cnpj:
                qs = Seller.objects.exclude(user=user).filter(cnpj=cnpj)
                if qs.exists():
                    raise serializers.ValidationError({"cnpj": "CNPJ já está em uso."})
            required = ["first_name", "last_name", "company_name", "cnpj", "phone_number"]
            missing = []
            for field in required:
                if field in attrs and attrs.get(field):
                    continue
                current = None
                if field in ("first_name", "last_name"):
                    current = getattr(user, field, None)
                elif seller:
                    current = getattr(seller, field, None)
                if not current:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError(
                    f"Para vendedor, informe: {', '.join(missing)}."
                )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        data = self.validated_data

        with transaction.atomic():
            if "first_name" in data:
                user.first_name = data.get("first_name", "")
            if "last_name" in data:
                user.last_name = data.get("last_name", "")
            try:
                user.full_clean()
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message_dict)
            user.save()

            if user.role == User.Role.CUSTOMER:
                customer, _created = Customer.objects.get_or_create(user=user)
                customer.first_name = user.first_name
                customer.last_name = user.last_name
                if "cpf" in data:
                    customer.cpf = data.get("cpf", customer.cpf)
                if "phone_number" in data:
                    customer.phone_number = data.get("phone_number", customer.phone_number)
                try:
                    customer.full_clean()
                except DjangoValidationError as e:
                    raise serializers.ValidationError(e.message_dict)
                customer.save()

            if user.role == User.Role.SELLER:
                seller, _created = Seller.objects.get_or_create(user=user)
                if "company_name" in data:
                    seller.company_name = data.get("company_name", seller.company_name)
                if "cnpj" in data:
                    seller.cnpj = data.get("cnpj", seller.cnpj)
                if "phone_number" in data:
                    seller.phone_number = data.get("phone_number", seller.phone_number)
                try:
                    seller.full_clean()
                except DjangoValidationError as e:
                    raise serializers.ValidationError(e.message_dict)
                seller.save()

        return user        


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "quantity_in_stock",
            "category",
            "seller",
            "image",
            "created_at",
        ]
        read_only_fields = ["id", "seller", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request.user, "seller_profile"):
            validated_data["seller"] = request.user.seller_profile
        return super().create(validated_data)

    def validate_price(self, value):
        if value is None:
            raise serializers.ValidationError("Preço é obrigatório.")
        if value <= 0:
            raise serializers.ValidationError("Preço deve ser maior que zero.")
        return value

    def validate_quantity_in_stock(self, value):
        if value is None:
            raise serializers.ValidationError("Estoque é obrigatório.")
        if value < 0:
            raise serializers.ValidationError("Estoque não pode ser negativo.")
        return value


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "quantity_in_stock",
            "category",
            "seller",
            "image",
            "created_at",
        ]
        read_only_fields = ["id", "seller", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


def normalize_serializer_errors(errors):
    normalized = []

    def walk(path, value):
        if isinstance(value, dict):
            for key, child in value.items():
                next_path = f"{path}.{key}" if path else str(key)
                walk(next_path, child)
            return
        if isinstance(value, list):
            for item in value:
                walk(path, item)
            return
        field = path or api_settings.NON_FIELD_ERRORS_KEY
        normalized.append({"field": field, "message": str(value)})

    walk("", errors)
    return normalized
