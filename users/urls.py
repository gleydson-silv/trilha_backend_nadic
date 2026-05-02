from django.urls import path, include
from . import views, frontend_views
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')

urlpatterns = [
    path('', RedirectView.as_view(url='/app/register/'), name='home'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
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
    path('', include(router.urls)),
    path('products/<int:product_id>/details/', views.product_details_with_stock, name='product_details_with_stock'),
    path('reports/revenue/', views.CompanyRevenueView.as_view(), name='company_revenue'),
    path('checkout/', views.checkout, name='checkout'),
    path('app/register/',frontend_views.app_register, name='app_register'),
    path('app/login/',frontend_views.app_login, name='app_login'),
    path('app/logout/', frontend_views.app_logout, name='app_logout'),
    path('app/login/google/<str:role>/', frontend_views.app_google_login, name='app_google_login'),
    path('app/forgot-password/', frontend_views.app_forgot_password, name='app_forgot_password'),
    path('app/profile/complete/', frontend_views.app_complete_profile, name='app_complete_profile'),
    path('app/profile/', frontend_views.app_profile, name='app_profile'),
    path('app/profile/details/', frontend_views.app_profile_details, name='app_profile_details'),
    path('app/security/', frontend_views.app_security, name='app_security'),
    path('app/cart/', frontend_views.app_cart, name='app_cart'),
    path('app/addresses/', frontend_views.app_addresses, name='app_addresses'),
    path('app/store/', frontend_views.app_store, name='app_store'),
    path('app/news/', frontend_views.app_news, name='app_news'),
    path('app/collections/', frontend_views.app_collections, name='app_collections'),
    path('app/accessories/', frontend_views.app_accessories, name='app_accessories'),
    path('app/about/', frontend_views.app_about, name='app_about'),
    path('app/support/', frontend_views.app_support, name='app_support'),
    path('app/contact/', frontend_views.app_contact, name='app_contact'),
    path('app/deliveries/', frontend_views.app_deliveries, name='app_deliveries'),
    path('app/returns/', frontend_views.app_returns, name='app_returns'),
    path('app/my-products/', frontend_views.app_my_products, name='app_my_products'),
    path('app/sales-report/', frontend_views.app_sales_report, name='app_sales_report'),
    path('app/products/create/', frontend_views.app_product_create, name='app_product_create'),
    path('app/products/edit/<int:pk>/', frontend_views.app_product_edit, name='app_product_edit'),
    path('app/products/delete/<int:pk>/', frontend_views.app_product_delete_confirm, name='app_product_delete_confirm'),
]
