"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views import View
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.shortcuts import render
from datetime import timedelta
from decimal import Decimal
import json

from sales.models import Sale, Member, SaleItem
from sales.utils import get_seven_days_sales, get_sales_ranking
from inventory.models import Inventory

# 仪表盘视图
class DashboardView(View):
    template_name = 'dashboard.html'
    
    def get(self, request):
        """仪表盘数据处理"""
        now = timezone.now()
        today = now.date()
        month_start = today.replace(day=1)
        
        # 今日数据 - 使用时区感知的时间范围查询，确保包含当天所有时间
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        today_sales = Sale.objects.filter(
            status='paid',
            created_at__range=(today_start, today_end)
        ).aggregate(
            total=Sum('final_amount'),
            count=Count('id')
        )
        
        # 本月数据
        month_end = timezone.datetime(today.year, today.month, 1) + timezone.timedelta(days=32)
        month_end = timezone.datetime(month_end.year, month_end.month, 1) - timezone.timedelta(days=1)
        month_start_aware = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))
        month_end_aware = timezone.make_aware(timezone.datetime.combine(month_end.date(), timezone.datetime.max.time()))
        
        month_sales = Sale.objects.filter(
            status='paid',
            created_at__range=(month_start_aware, month_end_aware)
        ).aggregate(
            total=Sum('final_amount'),
            count=Count('id')
        )
        
        # 近7天销售趋势 - 使用公共函数获取数据
        chart_labels, chart_data, _ = get_seven_days_sales()
        
        # 库存预警数量 - 库存低于最低预警值的商品数量
        low_stock_count = Inventory.objects.filter(
            quantity__lt=F('product__min_stock')
        ).count()
        
        # 会员总数 - 启用的会员数量
        member_count = Member.objects.filter(is_active=True).count()
        
        # 本月商品销售排行 - 使用公共函数获取数据
        top_products = get_sales_ranking(period='month', limit=10, include_barcode=False)
        
        # 最近销售记录
        recent_sales = Sale.objects.filter(
            status='paid'
        ).select_related('store').order_by('-created_at')[:10]
        
        return render(request, self.template_name, {
            'today_sales': today_sales['total'] or Decimal('0'),
            'today_orders': today_sales['count'] or 0,
            'month_sales': month_sales['total'] or Decimal('0'),
            'month_orders': month_sales['count'] or 0,
            'low_stock_count': low_stock_count,
            'member_count': member_count,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'top_products': top_products,
            'recent_sales': recent_sales,
        })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_required(DashboardView.as_view()), name='dashboard'),
    path('users/', include('users.urls')),
    path('inventory/', include('inventory.urls')),
    path('purchase/', include('purchase.urls')),
    path('sales/', include('sales.urls')),
    path('finance/', include('finance.urls')),
]