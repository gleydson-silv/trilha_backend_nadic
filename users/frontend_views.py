from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Product, User


@ensure_csrf_cookie
def app_register(request):
    return render(request, "register.html")


@ensure_csrf_cookie
def app_login(request):
    return render(request, "login.html")


@ensure_csrf_cookie
def app_forgot_password(request):
    return render(request, "forgot-password.html")


@ensure_csrf_cookie
def app_complete_profile(request):
    return render(request, "complete-profile.html")


def _has_value(value):
    return bool(str(value).strip()) if value is not None else False


def _profile_is_complete(user):
    if not user.is_authenticated:
        return False

    if user.role == User.Role.CUSTOMER:
        customer = getattr(user, "customer_profile", None)
        if not customer:
            return False
        return all(
            _has_value(field)
            for field in [
                user.first_name,
                user.last_name,
                customer.cpf,
                customer.phone_number,
            ]
        )

    if user.role == User.Role.SELLER:
        seller = getattr(user, "seller_profile", None)
        if not seller:
            return False
        return all(
            _has_value(field)
            for field in [
                user.first_name,
                user.last_name,
                seller.company_name,
                seller.cnpj,
                seller.phone_number,
            ]
        )

    return False


@ensure_csrf_cookie
def app_store(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    if not _profile_is_complete(user):
        role = user.role if user.role else ""
        redirect_url = "/app/profile/complete/"
        if role in (User.Role.CUSTOMER, User.Role.SELLER):
            redirect_url = f"{redirect_url}?role={role}"
        return redirect(redirect_url)

    products = Product.objects.all()
    return render(request, "store.html", {"products": products})
