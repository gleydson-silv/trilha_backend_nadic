from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/',views.logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('profile/complete/', views.complete_profile, name='complete_profile'),
]
