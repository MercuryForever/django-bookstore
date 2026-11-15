from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count, Avg
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

from sales.models import Sale, SaleItem
from sales.utils import get_seven_days_sales
from inventory.models import Store
from users.decorators import manager_required


@login_required
@manager_required
def dashboard(request):
    """财务仪表盘"""
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
    
    # 本月利润（销售额 - 成本）
    month_profit = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__range=(month_start_aware, month_end_aware)
    ).aggregate(
        profit=Sum(F('quantity') * (F('price') - F('cost_price')))
    )['profit'] or Decimal('0')
    
    # 近7天销售趋势 - 使用公共函数获取数据
    chart_labels, chart_data, _ = get_seven_days_sales()
    
    # 门店销售排行
    store_ranking = Sale.objects.filter(
        status='paid',
        created_at__range=(month_start_aware, month_end_aware)
    ).values(
        'store__name'
    ).annotate(
        total=Sum('final_amount'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    return render(request, 'finance/dashboard.html', {
        'today_sales': today_sales['total'] or Decimal('0'),
        'today_orders': today_sales['count'] or 0,
        'month_sales': month_sales['total'] or Decimal('0'),
        'month_orders': month_sales['count'] or 0,
        'month_profit': month_profit,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'store_ranking': store_ranking,
    })


@login_required
@manager_required
def daily_report(request):
    """日报表"""
    date_str = request.GET.get('date', '')
    
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.now().date()
    
    # 按门店统计
    store_stats = Sale.objects.filter(
        status='paid',
        created_at__date=report_date
    ).values(
        'store__id',
        'store__name'
    ).annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    ).order_by('-sales_amount')
    
    # 计算利润
    for stat in store_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date=report_date,
            sale__store_id=stat['store__id']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        stat['profit'] = profit
    
    # 汇总
    total = Sale.objects.filter(
        status='paid',
        created_at__date=report_date
    ).aggregate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    )
    
    total_profit = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__date=report_date
    ).aggregate(
        profit=Sum(F('quantity') * (F('price') - F('cost_price')))
    )['profit'] or Decimal('0')
    
    return render(request, 'finance/daily_report.html', {
        'report_date': report_date,
        'store_stats': store_stats,
        'total': total,
        'total_profit': total_profit,
    })


@login_required
@manager_required
def monthly_report(request):
    """月报表"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # 月初和月末
    from calendar import monthrange
    month_start = timezone.datetime(year, month, 1).date()
    month_end = timezone.datetime(year, month, monthrange(year, month)[1]).date()
    
    # 按天统计
    daily_stats = Sale.objects.filter(
        status='paid',
        created_at__date__gte=month_start,
        created_at__date__lte=month_end
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
    ).order_by('date')
    
    # 计算每日利润
    for stat in daily_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date=stat['date']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        stat['profit'] = profit
    
    # 按门店统计
    store_stats = Sale.objects.filter(
        status='paid',
        created_at__date__gte=month_start,
        created_at__date__lte=month_end
    ).values(
        'store__id',
        'store__name'
    ).annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    ).order_by('-sales_amount')
    
    # 计算门店利润
    for stat in store_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date__gte=month_start,
            sale__created_at__date__lte=month_end,
            sale__store_id=stat['store__id']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        stat['profit'] = profit
    
    # 月度汇总
    total = Sale.objects.filter(
        status='paid',
        created_at__date__gte=month_start,
        created_at__date__lte=month_end
    ).aggregate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    )
    
    total_profit = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__date__gte=month_start,
        sale__created_at__date__lte=month_end
    ).aggregate(
        profit=Sum(F('quantity') * (F('price') - F('cost_price')))
    )['profit'] or Decimal('0')
    
    # 图表数据
    chart_labels = [stat['date'].strftime('%d') for stat in daily_stats]
    chart_data = [float(stat['sales_amount'] or 0) for stat in daily_stats]
    
    return render(request, 'finance/monthly_report.html', {
        'year': year,
        'month': month,
        'month_start': month_start,
        'month_end': month_end,
        'daily_stats': daily_stats,
        'store_stats': store_stats,
        'total': total,
        'total_profit': total_profit,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    })


@login_required
@manager_required
def export_daily_report(request):
    """导出日报表到Excel"""
    date_str = request.GET.get('date', '')
    
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.now().date()
    
    # 创建工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'日报表_{report_date}'
    
    # 样式
    header_font = Font(bold=True)
    center_align = Alignment(horizontal='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 标题
    ws.merge_cells('A1:E1')
    ws['A1'] = f'日销售报表 - {report_date}'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = center_align
    
    # 表头
    headers = ['门店', '订单数', '销售额', '优惠金额', '利润']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    
    # 数据
    store_stats = Sale.objects.filter(
        status='paid',
        created_at__date=report_date
    ).values(
        'store__name'
    ).annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    ).order_by('-sales_amount')
    
    row = 4
    for stat in store_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date=report_date,
            sale__store__name=stat['store__name']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        
        ws.cell(row=row, column=1, value=stat['store__name']).border = thin_border
        ws.cell(row=row, column=2, value=stat['sales_count']).border = thin_border
        ws.cell(row=row, column=3, value=float(stat['sales_amount'] or 0)).border = thin_border
        ws.cell(row=row, column=4, value=float(stat['discount_amount'] or 0)).border = thin_border
        ws.cell(row=row, column=5, value=float(profit)).border = thin_border
        row += 1
    
    # 调整列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    
    # 返回响应
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="daily_report_{report_date}.xlsx"'
    wb.save(response)
    
    return response


@login_required
@manager_required
def export_monthly_report(request):
    """导出月报表到Excel"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # 月初和月末
    from calendar import monthrange
    month_start = timezone.datetime(year, month, 1).date()
    month_end = timezone.datetime(year, month, monthrange(year, month)[1]).date()
    
    # 创建工作簿
    wb = openpyxl.Workbook()
    
    # 按门店统计工作表
    ws_store = wb.active
    ws_store.title = f'按门店统计_{year}年{month}月'
    
    # 样式
    header_font = Font(bold=True)
    center_align = Alignment(horizontal='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 标题
    ws_store.merge_cells('A1:E1')
    ws_store['A1'] = f'月销售报表 - {year}年{month}月'
    ws_store['A1'].font = Font(bold=True, size=14)
    ws_store['A1'].alignment = center_align
    
    # 表头
    headers = ['门店', '订单数', '销售额', '优惠金额', '利润']
    for col, header in enumerate(headers, 1):
        cell = ws_store.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    
    # 按门店统计数据
    store_stats = Sale.objects.filter(
        status='paid',
        created_at__date__gte=month_start,
        created_at__date__lte=month_end
    ).values(
        'store__id',
        'store__name'
    ).annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
        discount_amount=Sum('discount_amount'),
    ).order_by('-sales_amount')
    
    row = 4
    for stat in store_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date__gte=month_start,
            sale__created_at__date__lte=month_end,
            sale__store_id=stat['store__id']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        
        ws_store.cell(row=row, column=1, value=stat['store__name']).border = thin_border
        ws_store.cell(row=row, column=2, value=stat['sales_count']).border = thin_border
        ws_store.cell(row=row, column=3, value=float(stat['sales_amount'] or 0)).border = thin_border
        ws_store.cell(row=row, column=4, value=float(stat['discount_amount'] or 0)).border = thin_border
        ws_store.cell(row=row, column=5, value=float(profit)).border = thin_border
        row += 1
    
    # 按天统计工作表
    ws_daily = wb.create_sheet(title=f'按天统计_{year}年{month}月')
    
    # 按天统计标题
    ws_daily.merge_cells('A1:D1')
    ws_daily['A1'] = f'月销售报表 - {year}年{month}月（按天统计）'
    ws_daily['A1'].font = Font(bold=True, size=14)
    ws_daily['A1'].alignment = center_align
    
    # 按天统计表头
    daily_headers = ['日期', '订单数', '销售额', '利润']
    for col, header in enumerate(daily_headers, 1):
        cell = ws_daily.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    
    # 按天统计数据
    daily_stats = Sale.objects.filter(
        status='paid',
        created_at__date__gte=month_start,
        created_at__date__lte=month_end
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        sales_count=Count('id'),
        sales_amount=Sum('final_amount'),
    ).order_by('date')
    
    daily_row = 4
    for stat in daily_stats:
        profit = SaleItem.objects.filter(
            sale__status='paid',
            sale__created_at__date=stat['date']
        ).aggregate(
            profit=Sum(F('quantity') * (F('price') - F('cost_price')))
        )['profit'] or Decimal('0')
        
        ws_daily.cell(daily_row, 1, value=stat['date']).border = thin_border
        ws_daily.cell(daily_row, 2, value=stat['sales_count']).border = thin_border
        ws_daily.cell(daily_row, 3, value=float(stat['sales_amount'] or 0)).border = thin_border
        ws_daily.cell(daily_row, 4, value=float(profit)).border = thin_border
        daily_row += 1
    
    # 调整列宽
    for ws in [ws_store, ws_daily]:
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        if ws == ws_store:
            ws.column_dimensions['E'].width = 15
    
    # 返回响应
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="monthly_report_{year}{month:02d}.xlsx"'
    wb.save(response)
    
    return response


@login_required
@manager_required
def profit_analysis(request):
    """利润分析"""
    # 时间范围
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)
    else:  # year
        start_date = today.replace(month=1, day=1)
    
    # 按商品分类统计利润
    category_profit = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__date__gte=start_date
    ).values(
        'product__category__name'
    ).annotate(
        revenue=Sum(F('quantity') * F('price')),
        cost=Sum(F('quantity') * F('cost_price')),
        profit=Sum(F('quantity') * (F('price') - F('cost_price'))),
        quantity=Sum('quantity')
    ).order_by('-profit')
    
    # 计算利润率
    for cat in category_profit:
        if cat['revenue'] and cat['revenue'] > 0:
            cat['margin'] = (cat['profit'] / cat['revenue'] * 100)
        else:
            cat['margin'] = 0
    
    # 商品利润排行
    product_profit = SaleItem.objects.filter(
        sale__status='paid',
        sale__created_at__date__gte=start_date
    ).values(
        'product__name',
        'product__barcode'
    ).annotate(
        revenue=Sum(F('quantity') * F('price')),
        profit=Sum(F('quantity') * (F('price') - F('cost_price'))),
        quantity=Sum('quantity')
    ).order_by('-profit')[:20]
    
    return render(request, 'finance/profit_analysis.html', {
        'period': period,
        'start_date': start_date,
        'category_profit': category_profit,
        'product_profit': product_profit,
    })