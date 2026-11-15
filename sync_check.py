import os
import django
from decimal import Decimal

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count
from datetime import timedelta
from sales.models import Sale, SaleItem
from sales.utils import get_seven_days_sales

# 检查近7天销售趋势数据一致性
print("=== 近7天销售趋势数据一致性检查 ===")

# 获取当前时间
today = timezone.now().date()
month_start = today.replace(day=1)

# 1. 测试公共函数
print("\n1. 测试公共函数 get_seven_days_sales():")
chart_labels, chart_data, full_data = get_seven_days_sales()
print(f"   返回数据长度: labels={len(chart_labels)}, data={len(chart_data)}, full_data={len(full_data)}")
print(f"   数据示例: {chart_labels[0]}: {chart_data[0]}")

# 2. 测试直接查询
print("\n2. 测试直接查询 Sale 模型:")
seven_days_ago = today - timedelta(days=6)
seven_days_ago_start = timezone.make_aware(timezone.datetime.combine(seven_days_ago, timezone.datetime.min.time()))
today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

daily_sales = Sale.objects.filter(
    status='paid',
    created_at__range=(seven_days_ago_start, today_end)
).annotate(
    date=TruncDate('created_at')
).values('date').annotate(
    total=Sum('final_amount')
).order_by('date')

print(f"   查询结果数量: {len(list(daily_sales))}")

# 3. 比较今日销售额
print("\n3. 比较今日销售额:")
today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

# 主仪表盘查询方式
today_sales_1 = Sale.objects.filter(
    status='paid',
    created_at__range=(today_start, today_end)
).aggregate(
    total=Sum('final_amount'),
    count=Count('id')
)

# 财务仪表盘查询方式
today_sales_2 = Sale.objects.filter(
    status='paid',
    created_at__range=(today_start, today_end)
).aggregate(
    total=Sum('final_amount'),
    count=Count('id')
)

print(f"   主仪表盘今日销售额: {today_sales_1['total'] or Decimal('0')}")
print(f"   财务仪表盘今日销售额: {today_sales_2['total'] or Decimal('0')}")
print(f"   一致: {today_sales_1 == today_sales_2}")

# 4. 比较本月销售额
print("\n4. 比较本月销售额:")
month_end = timezone.datetime(today.year, today.month, 1) + timezone.timedelta(days=32)
month_end = timezone.datetime(month_end.year, month_end.month, 1) - timezone.timedelta(days=1)
month_start_aware = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))
month_end_aware = timezone.make_aware(timezone.datetime.combine(month_end.date(), timezone.datetime.max.time()))

# 主仪表盘查询方式
month_sales_1 = Sale.objects.filter(
    status='paid',
    created_at__range=(month_start_aware, month_end_aware)
).aggregate(
    total=Sum('final_amount'),
    count=Count('id')
)

# 财务仪表盘查询方式
month_sales_2 = Sale.objects.filter(
    status='paid',
    created_at__range=(month_start_aware, month_end_aware)
).aggregate(
    total=Sum('final_amount'),
    count=Count('id')
)

print(f"   主仪表盘本月销售额: {month_sales_1['total'] or Decimal('0')}")
print(f"   财务仪表盘本月销售额: {month_sales_2['total'] or Decimal('0')}")
print(f"   一致: {month_sales_1 == month_sales_2}")

# 5. 检查状态过滤条件
print("\n5. 检查状态过滤条件:")
all_sales = Sale.objects.count()
paid_sales = Sale.objects.filter(status='paid').count()
pending_sales = Sale.objects.filter(status='pending').count()
cancelled_sales = Sale.objects.filter(status='cancelled').count()
refunded_sales = Sale.objects.filter(status='refunded').count()

print(f"   总销售单数量: {all_sales}")
print(f"   已支付销售单数量: {paid_sales}")
print(f"   待支付销售单数量: {pending_sales}")
print(f"   已取消销售单数量: {cancelled_sales}")
print(f"   已退款销售单数量: {refunded_sales}")

# 6. 检查近7天数据
print("\n6. 检查近7天数据:")
seven_days_data = Sale.objects.filter(
    status='paid',
    created_at__range=(seven_days_ago_start, today_end)
).count()
print(f"   近7天已支付销售单数量: {seven_days_data}")

print("\n=== 检查完成 ===")
