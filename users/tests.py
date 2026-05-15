from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Customer, Payment, Product, Seller, User


class UserAccountTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.complete_profile_url = reverse("complete_profile")
        self.email = "testuser@example.com"
        self.password = "StrongPassword123!"

    def test_register_user(self):
        data = {
            "email": self.email,
            "password": self.password,
            "role": "user",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.email).exists())

    def test_login_user(self):
        User.objects.create_user(email=self.email, password=self.password)
        data = {"email": self.email, "password": self.password}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["data"])

    def test_complete_profile_as_seller(self):
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)
        data = {
            "first_name": "John",
            "last_name": "Seller",
            "phone_number": "11-999999999",
            "company_name": "Test Company",
            "cnpj": "12.345.678/0001-90",
        }
        response = self.client.patch(self.complete_profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.SELLER)
        self.assertTrue(Seller.objects.filter(user=user).exists())
        self.assertEqual(user.seller_profile.company_name, "Test Company")

    def test_complete_profile_as_customer(self):
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)
        data = {
            "first_name": "Jane",
            "last_name": "Customer",
            "phone_number": "11-988888888",
            "cpf": "123.456.789-00",
        }
        response = self.client.patch(self.complete_profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.assertEqual(user.customer_profile.cpf, "123.456.789-00")

    def test_complete_profile_invalid_data(self):
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)
        data = {"first_name": "Incomplete", "company_name": "No CNPJ"}
        response = self.client.patch(self.complete_profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cnpj", response.data["details"][0]["message"])


class MarketplaceTestMixin:
    def _create_seller_with_product(self, stock=10):
        seller_user = User.objects.create_user(
            email="seller@example.com", password="StrongPassword123!"
        )
        seller_user.role = User.Role.SELLER
        seller_user.save()
        seller = Seller.objects.create(
            user=seller_user,
            company_name="Loja Teste",
            cnpj="12.345.678/0001-90",
            phone_number="11-999999999",
        )
        category = Category.objects.create(
            name="Categoria Teste", description="Desc"
        )
        product = Product.objects.create(
            name="Produto Teste",
            description="Desc",
            price=Decimal("50.00"),
            quantity_in_stock=stock,
            category=category,
            seller=seller,
        )
        return seller_user, product

    def _create_customer(self, email="customer@example.com"):
        customer_user = User.objects.create_user(
            email=email, password="StrongPassword123!"
        )
        customer_user.role = User.Role.CUSTOMER
        customer_user.first_name = "Jane"
        customer_user.last_name = "Customer"
        customer_user.save()
        Customer.objects.create(
            user=customer_user,
            first_name="Jane",
            last_name="Customer",
            cpf="123.456.789-00",
            phone_number="11-988888888",
        )
        return customer_user


class CheckoutTests(MarketplaceTestMixin, APITestCase):
    def setUp(self):
        self.checkout_url = reverse("api_checkout")
        self.seller_user, self.product = self._create_seller_with_product(stock=5)
        self.customer_user = self._create_customer()

    def test_checkout_success(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(
            self.checkout_url,
            {
                "items": [{"product_id": self.product.id, "quantity": 2}],
                "payment_method": "pix",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 3)
        order_id = response.data["data"]["id"]
        self.assertTrue(Payment.objects.filter(order_id=order_id).exists())

    def test_checkout_insufficient_stock(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(
            self.checkout_url,
            {
                "items": [{"product_id": self.product.id, "quantity": 99}],
                "payment_method": "pix",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 5)

    def test_checkout_requires_customer_profile(self):
        user = User.objects.create_user(
            email="noprofile@example.com", password="StrongPassword123!"
        )
        user.role = User.Role.CUSTOMER
        user.save()
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.checkout_url,
            {
                "items": [{"product_id": self.product.id, "quantity": 1}],
                "payment_method": "pix",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_cannot_checkout(self):
        self.client.force_authenticate(user=self.seller_user)
        response = self.client.post(
            self.checkout_url,
            {
                "items": [{"product_id": self.product.id, "quantity": 1}],
                "payment_method": "pix",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProductPermissionTests(MarketplaceTestMixin, APITestCase):
    def setUp(self):
        self.products_url = reverse("product-list")
        self.seller_a, self.product_a = self._create_seller_with_product()
        self.seller_b = User.objects.create_user(
            email="sellerb@example.com", password="StrongPassword123!"
        )
        self.seller_b.role = User.Role.SELLER
        self.seller_b.save()
        Seller.objects.create(
            user=self.seller_b,
            company_name="Outra Loja",
            cnpj="98.765.432/0001-10",
            phone_number="11-977777777",
        )
        self.customer = self._create_customer()

    def test_customer_cannot_create_product(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.products_url,
            {
                "name": "Novo",
                "description": "Desc",
                "price": "10.00",
                "quantity_in_stock": 1,
                "category": self.product_a.category_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_create_own_product(self):
        self.client.force_authenticate(user=self.seller_a)
        response = self.client.post(
            self.products_url,
            {
                "name": "Novo Produto",
                "description": "Desc",
                "price": "25.00",
                "quantity_in_stock": 3,
                "category": self.product_a.category_id,
            },
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_seller_cannot_update_other_seller_product(self):
        self.client.force_authenticate(user=self.seller_b)
        detail_url = reverse("product-detail", kwargs={"pk": self.product_a.pk})
        response = self.client.patch(
            detail_url, {"name": "Hack"}, format="json"
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
