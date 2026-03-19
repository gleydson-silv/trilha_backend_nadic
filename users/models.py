from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from .validators import (
    cpf_format_validator,
    cnpj_format_validator,
    phone_format_validator,
    validate_cpf,
    validate_cnpj,
)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)



class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'
        CUSTOMER = 'customer', 'Customer'
        SELLER = 'seller', 'Seller'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=255, null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', null=False, blank=False)
    first_name = models.CharField(max_length=50,null=False,blank=False)
    last_name = models.CharField(max_length=50,null=False, blank=False)
    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=False,
        blank=False,
        validators=[cpf_format_validator, validate_cpf],
    )
    phone_number = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        validators=[phone_format_validator],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile', null=False, blank= False)
    company_name = models.CharField(max_length=255,null=False, blank=False)
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        null=False,
        blank=False,
        validators=[cnpj_format_validator, validate_cnpj],
    )
    phone_number = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        validators=[phone_format_validator],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity_in_stock = models.IntegerField(validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.CharField(max_length=255, null=True, blank=True)



class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    state = models.CharField(max_length=20,choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered')
    ], default='pending')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])



class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=[
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('boleto', 'Boleto'),
        ('pix', 'Pix')
    ], default='credit_card')


class FinancialReport(models.Model):
    report_date = models.DateTimeField(auto_now_add=True)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2)


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    street = models.CharField(max_length=255,null=False, blank=False)
    number = models.CharField(max_length=10,default="s/n")
    city = models.CharField(max_length=100, null=False, blank=False)
    state = models.CharField(max_length=100, null=False, blank=False)
    zip_code = models.CharField(max_length=20, null=False, blank=False)
    country = models.CharField(max_length=100, null=False, blank=False)
