from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


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

