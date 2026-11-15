from django.contrib import admin
from .models import (
    Warehouse, Store, Category, Product, 
    Inventory, StockMovement, StockTransfer, StockTransferItem,
    StockCheck, StockCheckItem
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'location', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['is_active']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'warehouse', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['warehouse', 'is_active']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order']
    list_filter = ['parent']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'barcode', 'category', 'cost_price', 'sale_price', 'is_active']
    search_fields = ['name', 'barcode', 'isbn']
    list_filter = ['category', 'is_active']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['store', 'product', 'quantity', 'updated_at']
    search_fields = ['product__name', 'store__name']
    list_filter = ['store']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['store', 'product', 'movement_type', 'quantity', 'created_at']
    search_fields = ['product__name', 'reference_no']
    list_filter = ['movement_type', 'store']


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_no', 'from_store', 'to_store', 'status', 'created_at']
    list_filter = ['status']
    inlines = [StockTransferItemInline]