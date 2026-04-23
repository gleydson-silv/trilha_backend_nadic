from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, Seller, Customer

class UserAccountTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.complete_profile_url = reverse('complete_profile')
        self.email = "testuser@example.com"
        self.password = "StrongPassword123!"

    def test_register_user(self):
        """Verifica a criação de conta."""
        data = {
            "email": self.email,
            "password": self.password,
            "role": "user"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.email).exists())

    def test_login_user(self):
        """Verifica a autenticação e recebimento do token."""
        # Primeiro registra
        User.objects.create_user(email=self.email, password=self.password)
        
        data = {
            "email": self.email,
            "password": self.password
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])

    def test_complete_profile_as_seller(self):
        """Verifica a conclusão de perfil como Vendedor (Seller)."""
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)

        data = {
            "first_name": "John",
            "last_name": "Seller",
            "phone_number": "11-999999999",
            "company_name": "Test Company",
            "cnpj": "12.345.678/0001-90"
        }
        response = self.client.patch(self.complete_profile_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.SELLER)
        self.assertTrue(Seller.objects.filter(user=user).exists())
        self.assertEqual(user.seller_profile.company_name, "Test Company")

    def test_complete_profile_as_customer(self):
        """Verifica a conclusão de perfil como Cliente (Customer)."""
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)

        data = {
            "first_name": "Jane",
            "last_name": "Customer",
            "phone_number": "11-988888888",
            "cpf": "123.456.789-00"
        }
        response = self.client.patch(self.complete_profile_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.assertEqual(user.customer_profile.cpf, "123.456.789-00")

    def test_complete_profile_invalid_data(self):
        """Verifica erro ao enviar dados incompletos ou inválidos."""
        user = User.objects.create_user(email=self.email, password=self.password)
        self.client.force_authenticate(user=user)

        # Tentando ser vendedor sem CNPJ ou nome da empresa
        data = {
            "first_name": "Incomplete",
            "company_name": "No CNPJ"
        }
        response = self.client.patch(self.complete_profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cnpj", response.data['details'][0]['message'])
