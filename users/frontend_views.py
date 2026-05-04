from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import logout as django_logout
from .models import Product, User, Category


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
def app_logout(request):
    django_logout(request)
    return redirect("/app/login/")


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


def _consume_pending_role(request, user):
    if not user.is_authenticated:
        return

    pending_role = request.session.pop("pending_role", None)
    if pending_role not in (User.Role.CUSTOMER, User.Role.SELLER):
        return

    has_customer = hasattr(user, "customer_profile")
    has_seller = hasattr(user, "seller_profile")
    has_profile = has_customer or has_seller

    if user.role == User.Role.USER or (not has_profile and user.role != pending_role):
        user.role = pending_role
        user.save()


@ensure_csrf_cookie
def app_store(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)

    if not _profile_is_complete(user):
        role = user.role if user.role else ""
        redirect_url = "/app/profile/complete/"
        if role in (User.Role.CUSTOMER, User.Role.SELLER):
            redirect_url = f"{redirect_url}?role={role}"
        return redirect(redirect_url)
    if user.role == User.Role.CUSTOMER:
        queryset = Product.objects.all().order_by("-created_at")
        
        category_id = request.GET.get("category")
        search_query = request.GET.get("search")
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
            
        categories = Category.objects.all()
            
        return render(request, "store_customer.html", {
            "products": queryset,
            "categories": categories
        })
    if user.role == User.Role.SELLER:
        # Vendedor vê apenas seus produtos na seção "Meus Produtos" da store
        products = Product.objects.filter(seller=user.seller_profile)
        return render(request, "store_seller.html", {"products": products})



@ensure_csrf_cookie
def app_google_login(request, role):
    if role not in (User.Role.CUSTOMER, User.Role.SELLER):
        return redirect("/app/login/")
    user = request.user
    if user.is_authenticated:
        has_customer = hasattr(user, "customer_profile")
        has_seller = hasattr(user, "seller_profile")
        has_profile = has_customer or has_seller
        if user.role == User.Role.USER or (not has_profile and user.role != role):
            user.role = role
            user.save()
        return redirect("/app/store/")

    request.session["pending_role"] = role
    return redirect("/accounts/google/login/?next=/app/store/")


@ensure_csrf_cookie
def app_complete_profile(request):
    user = request.user
    if user.is_authenticated:
        _consume_pending_role(request, user)
    return render(request, "complete-profile.html")


@ensure_csrf_cookie
def app_profile(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)

    customer = getattr(user, "customer_profile", None)
    seller = getattr(user, "seller_profile", None)
    role = user.role

    payload = {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "role": role,
    }

    if seller:
        payload.update(
            {
                "company_name": seller.company_name,
                "cnpj": seller.cnpj,
                "phone_number": seller.phone_number,
            }
        )
    elif customer:
        payload.update(
            {
                "cpf": customer.cpf,
                "phone_number": customer.phone_number,
            }
        )

    return render(request, "profile.html", {"profile": payload})


@ensure_csrf_cookie
def app_profile_details(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)

    customer = getattr(user, "customer_profile", None)
    seller = getattr(user, "seller_profile", None)
    role = user.role

    payload = {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "role": role,
    }

    if seller:
        payload.update(
            {
                "company_name": seller.company_name,
                "cnpj": seller.cnpj,
                "phone_number": seller.phone_number,
            }
        )
    elif customer:
        payload.update(
            {
                "cpf": customer.cpf,
                "phone_number": customer.phone_number,
            }
        )

    return render(request, "profile-details.html", {"profile": payload})


@ensure_csrf_cookie
def app_cart(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "cart.html")


@ensure_csrf_cookie
def app_addresses(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)

    customer = getattr(user, "customer_profile", None)
    addresses = list(customer.addresses.all()) if customer else []

    return render(request, "addresses.html", {"addresses": addresses})


@ensure_csrf_cookie
def app_security(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)

    payload = {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "role": user.role,
        "two_factor_enabled": user.two_factor_enabled,
    }

    return render(request, "security.html", {"profile": payload})


@ensure_csrf_cookie
def app_news(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "news.html")


@ensure_csrf_cookie
def app_collections(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "collections.html")


@ensure_csrf_cookie
def app_accessories(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "accessories.html")


@ensure_csrf_cookie
def app_about(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "about.html")

@ensure_csrf_cookie
def app_contact(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "contact.html")

@ensure_csrf_cookie
def app_faq(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "faq.html")

@ensure_csrf_cookie
def app_support(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "support.html")


@ensure_csrf_cookie
def app_deliveries(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "deliveries.html")


@ensure_csrf_cookie
def app_returns(request):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    
    if user.role != User.Role.CUSTOMER:
        return redirect("/app/store/")
        
    return render(request, "returns.html")


@ensure_csrf_cookie
def app_my_products(request):
    user = request.user
    if not user.is_authenticated or user.role != User.Role.SELLER:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    products = Product.objects.filter(seller=user.seller_profile)
    return render(request, "my_products.html", {"products": products})


@ensure_csrf_cookie
def app_sales_report(request):
    user = request.user
    if not user.is_authenticated or user.role != User.Role.SELLER:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "sales_report.html")


@ensure_csrf_cookie
def app_product_create(request):
    user = request.user
    if not user.is_authenticated or user.role != User.Role.SELLER:
        return redirect("/app/login/")

    _consume_pending_role(request, user)
    return render(request, "product_create.html")


@ensure_csrf_cookie
def app_product_edit(request, pk):
    user = request.user
    if not user.is_authenticated or user.role != User.Role.SELLER:
        return redirect("/app/login/")

    product = get_object_or_404(Product, pk=pk, seller__user=user)
    categories = Category.objects.all()

    _consume_pending_role(request, user)
    return render(request, "product_edit.html", {
        "product": product,
        "categories": categories
    })


@ensure_csrf_cookie
def app_product_delete_confirm(request, pk):
    user = request.user
    if not user.is_authenticated or user.role != User.Role.SELLER:
        return redirect("/app/login/")

    product = get_object_or_404(Product, pk=pk, seller__user=user)
    
    _consume_pending_role(request, user)
    return render(request, "product_delete_confirm.html", {
        "product": product
    })


@ensure_csrf_cookie
def app_product_detail(request, pk):
    user = request.user
    if not user.is_authenticated:
        return redirect("/app/login/")

    product = get_object_or_404(Product, pk=pk)
    
    _consume_pending_role(request, user)
    return render(request, "product_detail.html", {
        "product": product
    })
