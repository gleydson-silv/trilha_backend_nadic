from django.contrib import admin
from .models import Product, Category

class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'quantity_in_stock', 'created_at']

admin.site.register(Product, AdminProduct)


class AdminCategory(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']

admin.site.register(Category, AdminCategory)


