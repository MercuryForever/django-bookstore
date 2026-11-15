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
from sales.models import Sale
from sales.utils import get_seven_days_sales

# 检查销售数据的时间分布
print("=== 销售数据时间分布检查 ===")

# 获取当前时间
now = timezone.now()
today = now.date()
print(f"当前时间: {now}")
print(f"当前日期: {today}")

# 获取近7天的日期范围
print("\n1. 近7天日期范围:")
seven_days_ago = today - timedelta(days=6)
print(f"   开始日期: {seven_days_ago}")
print(f"   结束日期: {today}")
print(f"   日期列表:")
for i in range(7):
    date = seven_days_ago + timedelta(days=i)
    print(f"      {i+1}. {date}")

# 查询所有销售数据的时间分布
print("\n2. 所有销售数据的时间分布:")
daily_sales_all = Sale.objects.filter(
    status='paid'
).annotate(
    date=TruncDate('created_at')
).values('date').annotate(
    count=Count('id'),
    total=Sum('final_amount')
).order_by('-date')

print(f"   总共有 {len(list(daily_sales_all))} 天的数据:")
for day in daily_sales_all[:10]:  # 只显示最近10天
    print(f"      {day['date']}: {day['count']} 笔订单，总计 {day['total'] or Decimal('0')} 元")

# 查询近7天的销售数据
print("\n3. 近7天销售数据查询结果:")
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

print(f"   近7天内有销售数据的天数: {len(list(daily_sales))}")

# 检查get_seven_days_sales函数的返回结果
print("\n4. get_seven_days_sales函数返回结果:")
chart_labels, chart_data, full_data = get_seven_days_sales()
print(f"   返回数据长度: labels={len(chart_labels)}, data={len(chart_data)}, full_data={len(full_data)}")
print(f"   详细数据:")
for i, (label, data, full) in enumerate(zip(chart_labels, chart_data, full_data)):
    print(f"      {i+1}. {label} ({full['date']}): {data} 元")

# 检查是否有最近的测试数据
print("\n5. 检查最近2天的详细销售数据:")
recent_start = today - timedelta(days=1)
recent_start_datetime = timezone.make_aware(timezone.datetime.combine(recent_start, timezone.datetime.min.time()))

recent_sales = Sale.objects.filter(
    status='paid',
    created_at__gte=recent_start_datetime
).order_by('-created_at')[:20]

print(f"   最近2天内有 {len(list(recent_sales))} 笔销售订单:")
for sale in recent_sales:
    print(f"      {sale.created_at} - {sale.order_no} - {sale.final_amount} 元 - 门店: {sale.store.name}")

print("\n=== 检查完成 ===")
