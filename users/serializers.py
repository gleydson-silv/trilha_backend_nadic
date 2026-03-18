from rest_framework import serializers
from .models import User, Customer, Seller


class RegisterSerializer(serializers.ModelSerializer):
    cpf = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cnpj = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'role',
            'first_name',
            'last_name',
            'cpf',
            'phone_number',
            'company_name',
            'cnpj',
        ]

        extra_kwargs = {
            'password': {'write_only': True}  
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        cpf = validated_data.pop("cpf", None)
        phone_number = validated_data.pop("phone_number", None)
        company_name = validated_data.pop("company_name", None)
        cnpj = validated_data.pop("cnpj", None)

        role = validated_data.get("role", User.Role.USER)
        user = User.objects.create_user(password=password, **validated_data)

        if role == User.Role.CUSTOMER:
            Customer.objects.create(
                user=user,
                first_name=user.first_name,
                last_name=user.last_name,
                cpf=cpf,
                phone_number=phone_number,
            )
        elif role == User.Role.SELLER:
            Seller.objects.create(
                user=user,
                company_name=company_name,
                cnpj=cnpj,
                phone_number=phone_number,
            )

        return user

    def validate(self, attrs):
        role = attrs.get("role", User.Role.USER)
        if role == User.Role.ADMIN:
            raise serializers.ValidationError("Role admin não é permitido no registro.")
        if role == User.Role.CUSTOMER:
            if not attrs.get("first_name") or not attrs.get("last_name"):
                raise serializers.ValidationError(
                    "Para cliente, informe first_name e last_name."
                )
            if not attrs.get("cpf") or not attrs.get("phone_number"):
                raise serializers.ValidationError(
                    "Para cliente, informe cpf e phone_number."
                )
        if role == User.Role.SELLER:
            if not attrs.get("company_name") or not attrs.get("cnpj"):
                raise serializers.ValidationError(
                    "Para vendedor, informe company_name e cnpj."
                )
            if not attrs.get("phone_number"):
                raise serializers.ValidationError(
                    "Para vendedor, informe phone_number."
                )
        return attrs
        
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
