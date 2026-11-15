from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceive


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact', 'phone', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['is_active']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'supplier', 'warehouse', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'supplier']
    inlines = [PurchaseOrderItemInline]


@admin.register(PurchaseReceive)
class PurchaseReceiveAdmin(admin.ModelAdmin):
    list_display = ['receive_no', 'order', 'store', 'created_at']