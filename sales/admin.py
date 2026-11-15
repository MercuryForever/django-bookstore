from django.contrib import admin
from .models import Member, PointsRecord, Sale, SaleItem


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_no', 'name', 'phone', 'points', 'total_amount', 'is_active']
    search_fields = ['member_no', 'name', 'phone']
    list_filter = ['is_active']


@admin.register(PointsRecord)
class PointsRecordAdmin(admin.ModelAdmin):
    list_display = ['member', 'record_type', 'points', 'balance', 'created_at']
    list_filter = ['record_type']


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'store', 'member', 'status', 'final_amount', 'created_at']
    list_filter = ['status', 'store', 'payment_method']
    inlines = [SaleItemInline]