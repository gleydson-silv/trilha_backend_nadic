from django.urls import path
from . import views,frontend_views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/app/register/'), name='home'),
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
    path('account/2fa/enable/', views.enable_2fa, name='enable_2fa'),
    path('account/2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('products/', views.products_list_create, name='products_list_create'),
    path('products/<int:product_id>/', views.product_detail_update_delete, name='product_detail_update_delete'),
    path('products/<int:product_id>/details/', views.product_details_with_stock, name='product_details_with_stock'),
    path('categories/', views.categories_list_create, name='categories_list_create'),
    path('categories/<int:category_id>/', views.category_detail_update_delete, name='category_detail_update_delete'),
    path('reports/revenue/', views.company_revenue, name='company_revenue'),
    path('app/register/',frontend_views.app_register, name='app_register'),
    path('app/login/',frontend_views.app_login, name='app_login'),
    path('app/login/google/', frontend_views.app_google_login, name='app_google_login'),
    path('app/forgot-password/', frontend_views.app_forgot_password, name='app_forgot_password'),
    path('app/profile/complete/', frontend_views.app_complete_profile, name='app_complete_profile'),
]
