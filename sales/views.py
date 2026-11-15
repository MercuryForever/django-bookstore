from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, F, Q, Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from decimal import Decimal
import json
import csv

from .models import Member, Sale, SaleItem, PointsRecord
from .forms import MemberForm
from .utils import get_seven_days_sales
from inventory.models import Store, Product, Inventory, StockMovement
from users.decorators import manager_required, cashier_required


# ==================== 会员管理 ====================

@login_required
@manager_required
def member_list(request):
    """会员列表"""
    members = Member.objects.all()
    
    search = request.GET.get('search', '')
    if search:
        members = members.filter(
            Q(member_no__icontains=search) |
            Q(name__icontains=search) |
            Q(phone__icontains=search)
        )
    
    paginator = Paginator(members, 20)
    page = request.GET.get('page', 1)
    members = paginator.get_page(page)
    
    return render(request, 'sales/member_list.html', {
        'members': members,
        'search': search,
    })


@login_required
@manager_required
def member_create(request):
    """创建会员"""
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.member_no = Member.generate_member_no()
            member.save()
            messages.success(request, f'会员 {member.name} 创建成功，卡号: {member.member_no}')
            return redirect('sales:member_list')
    else:
        form = MemberForm()
    
    return render(request, 'sales/member_form.html', {
        'form': form,
        'title': '新增会员'
    })


@login_required
@manager_required
def member_detail(request, pk):
    """会员详情"""
    member = get_object_or_404(Member, pk=pk)
    
    # 获取消费记录
    sales = member.sales.filter(status='paid').order_by('-created_at')[:20]
    
    # 获取积分记录
    points_records = member.points_records.all()[:20]
    
    return render(request, 'sales/member_detail.html', {
        'member': member,
        'sales': sales,
        'points_records': points_records,
    })


@login_required
@manager_required
def member_update(request, pk):
    """更新会员信息"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'会员 {member.name} 信息更新成功')
            return redirect('sales:member_detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    
    return render(request, 'sales/member_form.html', {
        'form': form,
        'title': '编辑会员',
        'member': member
    })


# ==================== 收银台 ====================

@login_required
@cashier_required
def pos(request):
    """收银台"""
    # 获取当前用户所属门店
    store = None
    if hasattr(request.user, 'employee') and request.user.employee.store:
        store = request.user.employee.store
    else:
        # 如果没有门店，取第一个
        store = Store.objects.filter(is_active=True).first()
    
    # 获取门店商品库存
    products = Product.objects.filter(is_active=True)
    
    return render(request, 'sales/pos.html', {
        'store': store,
        'products': products,
    })


@login_required
@cashier_required
def pos_checkout(request):
    """收银结算"""
    if request.method != 'POST':
        return JsonResponse({'error': '无效请求'}, status=400)
    
    try:
        data = json.loads(request.body)
        store_id = data.get('store_id')
        member_id = data.get('member_id')
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'cash')
        
        if not store_id or not items:
            return JsonResponse({'error': '缺少必要参数'}, status=400)
        
        store = Store.objects.get(pk=store_id)
        member = Member.objects.get(pk=member_id) if member_id else None
        
        with transaction.atomic():
            # 创建销售订单
            sale = Sale.objects.create(
                order_no=Sale.generate_order_no(),
                store=store,
                member=member,
                cashier=request.user,
            )
            
            total_amount = Decimal('0')
            
            for item_data in items:
                product = Product.objects.get(pk=item_data['product_id'])
                quantity = int(item_data['quantity'])
                price = Decimal(str(item_data['price']))
                
                # 检查库存（使用行锁）
                inventory = Inventory.objects.select_for_update().get(
                    store=store,
                    product=product
                )
                
                if inventory.quantity < quantity:
                    raise ValueError(f'{product.name} 库存不足')
                
                # 创建销售明细
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    price=price,
                    cost_price=product.cost_price
                )
                
                total_amount += price * quantity
                
                # 扣减库存
                before_qty = inventory.quantity
                inventory.quantity -= quantity
                inventory.save()
                
                # 记录库存变动
                StockMovement.objects.create(
                    store=store,
                    product=product,
                    movement_type='sale_out',
                    quantity=-quantity,
                    before_quantity=before_qty,
                    after_quantity=inventory.quantity,
                    reference_no=sale.order_no,
                    operator=request.user,
                    remark='销售出库'
                )
            
            # 更新订单金额
            sale.total_amount = total_amount
            sale.calculate_discount()  # 计算折扣（周三88折）
            sale.save()
            
            # 完成支付
            sale.complete_payment(payment_method)
            
        return JsonResponse({
            'success': True,
            'order_no': sale.order_no,
            'total_amount': str(sale.total_amount),
            'discount_amount': str(sale.discount_amount),
            'final_amount': str(sale.final_amount),
            'points_earned': sale.points_earned,
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'error': '商品不存在'}, status=400)
    except Inventory.DoesNotExist:
        return JsonResponse({'error': '商品库存记录不存在'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_member_search(request):
    """会员搜索 API"""
    keyword = request.GET.get('q', '')
    
    if not keyword:
        return JsonResponse({'members': []})
    
    members = Member.objects.filter(
        Q(member_no__icontains=keyword) |
        Q(name__icontains=keyword) |
        Q(phone__icontains=keyword),
        is_active=True
    )[:10]
    
    return JsonResponse({
        'members': [
            {
                'id': m.id,
                'member_no': m.member_no,
                'name': m.name,
                'phone': m.phone,
                'points': m.points,
            }
            for m in members
        ]
    })


@login_required
def api_check_discount(request):
    """检查是否有折扣 API"""
    # 周三88折
    is_wednesday = timezone.now().weekday() == 2
    
    return JsonResponse({
        'has_discount': is_wednesday,
        'discount_rate': 0.88 if is_wednesday else 1.0,
        'discount_name': '周三会员日88折' if is_wednesday else None,
    })


# ==================== 销售记录 ====================

@login_required
@manager_required
def sale_list(request):
    """销售记录列表"""
    sales = Sale.objects.select_related('store', 'member', 'cashier').filter(
        status='paid'
    )
    
    # 门店筛选
    store_id = request.GET.get('store', '')
    if store_id:
        sales = sales.filter(store_id=store_id)
    
    # 日期范围
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        sales = sales.filter(created_at__date__gte=start_date)
    if end_date:
        sales = sales.filter(created_at__date__lte=end_date)
    
    # 会员筛选
    member_search = request.GET.get('member', '')
    if member_search:
        sales = sales.filter(
            Q(member__name__icontains=member_search) |
            Q(member__phone__icontains=member_search)
        )
    
    paginator = Paginator(sales, 30)
    page = request.GET.get('page', 1)
    sales = paginator.get_page(page)
    
    stores = Store.objects.filter(is_active=True)
    
    return render(request, 'sales/sale_list.html', {
        'sales': sales,
        'stores': stores,
        'store_id': store_id,
        'start_date': start_date,
        'end_date': end_date,
        'member_search': member_search,
    })


@login_required
@manager_required
def sale_detail(request, pk):
    """销售详情"""
    sale = get_object_or_404(
        Sale.objects.select_related('store', 'member', 'cashier')
        .prefetch_related('items__product'),
        pk=pk
    )
    
    return render(request, 'sales/sale_detail.html', {
        'sale': sale
    })


# ==================== 销售统计 ====================

@login_required
@manager_required
def sales_ranking(request):
    """商品销售排行"""
    # 时间范围
    period = request.GET.get('period', 'month')
    
    # 销售排行 - 使用公共函数获取数据
    ranking = get_sales_ranking(period=period, limit=50, include_barcode=True)
    
    return render(request, 'sales/sales_ranking.html', {
        'ranking': ranking,
        'period': period,
        'start_date': start_date,
    })


@login_required
@manager_required
def export_sales(request):
    """导出销售数据"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    sales = Sale.objects.filter(status='paid').select_related('store', 'member')
    
    if start_date:
        sales = sales.filter(created_at__date__gte=start_date)
    if end_date:
        sales = sales.filter(created_at__date__lte=end_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_export.csv"'
    response.write('\ufeff'.encode('utf8'))  # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow(['订单号', '门店', '会员', '商品总额', '优惠金额', '实付金额', '支付方式', '创建时间'])
    
    for sale in sales:
        writer.writerow([
            sale.order_no,
            sale.store.name,
            sale.member.name if sale.member else '-',
            sale.total_amount,
            sale.discount_amount,
            sale.final_amount,
            sale.get_payment_method_display(),
            sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])



    return response

# ==================== 销售趋势 API ====================

@login_required
@manager_required
def sales_trend(request):
    """近7天销售趋势数据（用于图表）"""
    if request.method != 'GET':
        return JsonResponse({'error': '仅支持 GET 请求'}, status=405)

    # 使用公共函数获取数据
    _, _, full_data = get_seven_days_sales()

    return JsonResponse({'data': full_data})