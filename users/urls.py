from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/',views.logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('change-password/', views.change_password, name='change_password'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/update/partial/', views.update_profile_partial, name='partial_update_profile'),
    path('profile/complete/', views.complete_profile, name='complete_profile'),
    path('profile/address/', views.register_address, name='register_address'),
    path('cep/<str:cep>/', views.consultar_cep, name='consultar_cep'),
    path('account/delete/', views.delete_account, name='delete_account'),
    path('account/2fa/verify/', views.verify_2fa, name='verify_2fa'),
]
