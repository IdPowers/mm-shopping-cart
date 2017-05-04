from django.contrib import admin

from .models import CartItem

class CartItemAdmin(admin.ModelAdmin):
    pass

admin.site.register(CartItem, CartItemAdmin)
