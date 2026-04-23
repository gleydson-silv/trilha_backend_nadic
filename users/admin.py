from django.contrib import admin
from .models import Product, Category, User

class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'quantity_in_stock', 'created_at']

admin.site.register(Product, AdminProduct)


class AdminCategory(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']

admin.site.register(Category, AdminCategory)


class AdminUser(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
admin.site.register(User, AdminUser)


