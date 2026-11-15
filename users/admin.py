from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'store', 'phone', 'created_at']
    list_filter = ['role', 'store']
    search_fields = ['user__username', 'user__first_name', 'phone']