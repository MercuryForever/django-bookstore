#!/usr/bin/env python3
"""检查销售数据的脚本"""

import os
import sys

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.utils import timezone
from sales.models import Sale

# 获取当前时间和今天的日期
now = timezone.now()
today = now.date()

print(f"当前时间: {now}")
print(f"今天日期: {today}")

# 查询今天的销售记录（使用与dashboard相同的查询逻辑）
today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

print(f"查询时间范围: {today_start} 到 {today_end}")

# 使用与dashboard相同的查询
today_sales = Sale.objects.filter(
    status='paid',
    created_at__range=(today_start, today_end)
)

print(f"今天销售记录数量: {today_sales.count()}")

# 显示前5条销售记录
print("\n前5条销售记录:")
for sale in today_sales[:5]:
    print(f"订单号: {sale.order_no}")
    print(f"  状态: {sale.status}")
    print(f"  创建时间: {sale.created_at}")
    print(f"  支付时间: {sale.paid_at}")
    print(f"  总金额: {sale.total_amount}")
    print(f"  最终金额: {sale.final_amount}")
    print(f"  优惠金额: {sale.discount_amount}")
    print()

# 查询近7天的销售记录
seven_days_ago = today - timezone.timedelta(days=6)
seven_days_ago_start = timezone.make_aware(timezone.datetime.combine(seven_days_ago, timezone.datetime.min.time()))

print(f"\n近7天销售记录数量（从 {seven_days_ago} 到 {today}）:")
seven_day_sales = Sale.objects.filter(
    status='paid',
    created_at__range=(seven_days_ago_start, today_end)
)
print(f"近7天销售记录总数: {seven_day_sales.count()}")

# 按日期分组统计
print("\n近7天每日销售统计:")
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

daily_sales = seven_day_sales.annotate(
    date=TruncDate('created_at')
).values('date').annotate(
    total=Sum('final_amount'),
    count=Count('id')
).order_by('date')

for day in daily_sales:
    print(f"  {day['date']}: 金额 = {day['total']}, 订单数 = {day['count']}")
