from .address_views import consultar_cep, register_address
from .auth_views import (
    LoginView,
    RegisterView,
    change_password,
    disable_2fa,
    enable_2fa,
    forgot_password,
    logout,
    reset_password,
    verify_2fa,
)
from .category_views import CategoryViewSet
from .order_views import CheckoutView, CompanyRevenueView
from .product_views import ProductViewSet, product_details_with_stock
from .profile_views import (
    complete_profile,
    delete_account,
    profile,
    update_profile,
    update_profile_partial,
)

__all__ = [
    "RegisterView",
    "LoginView",
    "logout",
    "forgot_password",
    "reset_password",
    "change_password",
    "verify_2fa",
    "enable_2fa",
    "disable_2fa",
    "complete_profile",
    "profile",
    "update_profile",
    "update_profile_partial",
    "delete_account",
    "consultar_cep",
    "register_address",
    "ProductViewSet",
    "product_details_with_stock",
    "CategoryViewSet",
    "CompanyRevenueView",
    "CheckoutView",
]
