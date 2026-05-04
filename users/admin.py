from django.contrib import admin
from .models import Product, Category, User, Seller, Customer

from django.utils.html import format_html

class AdminProduct(admin.ModelAdmin):
    list_display = ['image_preview', 'name', 'price', 'quantity_in_stock', 'created_at']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 4px; object-fit: cover;" />', obj.image.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview'

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
admin.site.register(Seller)
admin.site.register(Customer)


