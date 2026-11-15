from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from sales.models import Sale, SaleItem

def get_seven_days_sales():
    """
    获取近7天销售趋势数据
    返回格式：(chart_labels, chart_data, full_data)
    - chart_labels: 日期标签列表，格式如 ['01-01', '01-02']
    - chart_data: 销售额数据列表，格式如 [100.0, 200.0]
    - full_data: 完整数据列表，包含日期和销售额，格式如 [{'date': '2026-01-01', 'value': 100.0}]
    """
    # 使用本地时间而非UTC时间，避免时区转换问题
    now = timezone.localtime(timezone.now())
    today = now.date()
    seven_days_ago = today - timedelta(days=6)
    
    # 使用本地时区的时间范围查询
    seven_days_ago_start = timezone.make_aware(timezone.datetime.combine(seven_days_ago, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # 查询近7天销售数据 - 确保使用TruncDate正确处理时区
    daily_sales = Sale.objects.filter(
        status='paid',
        created_at__range=(seven_days_ago_start, today_end)
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('final_amount')
    ).order_by('date')
    
    # 构建数据字典，便于查找
    sales_dict = {item['date']: item['total'] for item in daily_sales}
    
    # 构建完整数据
    chart_labels = []
    chart_data = []
    full_data = []
    
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        date_str = date.strftime('%m-%d')
        full_date_str = date.strftime('%Y-%m-%d')
        
        total = sales_dict.get(date, Decimal('0'))
        total_float = float(total or 0)
        
        chart_labels.append(date_str)
        chart_data.append(total_float)
        full_data.append({
            'date': full_date_str,
            'value': total_float
        })
    
    return chart_labels, chart_data, full_data

def get_sales_ranking(period='month', limit=10, include_barcode=False):
    """
    获取商品销售排行数据
    参数：
    - period: 时间范围，可选值：day, week, month
    - limit: 返回结果数量
    - include_barcode: 是否包含商品条形码
    返回：销售排行数据列表
    """
    now = timezone.now()
    today = now.date()
    
    # 确定时间范围
    if period == 'day':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=6)
        end_date = today
    else:  # month
        start_date = today.replace(day=1)
        end_date = today
    
    # 使用时区感知的时间范围查询
    start_datetime = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
    end_datetime = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
    
    # 确定返回字段
    values_fields = [
        'product__name',
        'product__id'
    ]
    if include_barcode:
        values_fields.append('product__barcode')
    
    # 查询销售排行
    ranking = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__range=(start_datetime, end_datetime)
    ).values(
        *values_fields
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('price'))
    ).order_by('-total_quantity')[:limit]
    
    return ranking
