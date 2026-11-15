from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    Store, Product, Inventory, StockMovement, 
    StockTransfer, StockTransferItem, StockCheck, StockCheckItem
)
from users.decorators import manager_required


# ==================== 库存查询 ====================

@login_required
@manager_required
def inventory_list(request):
    """库存列表"""
    inventories = Inventory.objects.select_related('store', 'product__category').all()
    
    # 门店筛选
    store_id = request.GET.get('store', '')
    if store_id:
        inventories = inventories.filter(store_id=store_id)
    elif hasattr(request.user, 'employee') and request.user.employee.store:
        # 默认显示当前用户所属门店
        inventories = inventories.filter(store=request.user.employee.store)
    
    # 商品搜索
    search = request.GET.get('search', '')
    if search:
        inventories = inventories.filter(
            Q(product__name__icontains=search) | 
            Q(product__barcode__icontains=search)
        )
    
    # 库存预警筛选
    low_stock = request.GET.get('low_stock', '')
    if low_stock:
        inventories = inventories.filter(quantity__lt=F('product__min_stock'))
    
    # 排序
    sort = request.GET.get('sort', '-updated_at')
    inventories = inventories.order_by(sort)
    
    paginator = Paginator(inventories, 50)
    page = request.GET.get('page', 1)
    inventories = paginator.get_page(page)
    
    stores = Store.objects.filter(is_active=True)
    
    return render(request, 'inventory/inventory_list.html', {
        'inventories': inventories,
        'stores': stores,
        'store_id': store_id,
        'search': search,
        'low_stock': low_stock,
        'sort': sort,
    })


@login_required
@manager_required
def inventory_detail(request, pk):
    """库存详情（库存变动历史）"""
    inventory = get_object_or_404(
        Inventory.objects.select_related('store', 'product'),
        pk=pk
    )
    
    # 获取库存变动记录
    movements = StockMovement.objects.filter(
        store=inventory.store,
        product=inventory.product
    ).select_related('operator').order_by('-created_at')[:50]
    
    return render(request, 'inventory/inventory_detail.html', {
        'inventory': inventory,
        'movements': movements,
    })


@login_required
@manager_required
def low_stock_list(request):
    """库存预警列表"""
    inventories = Inventory.objects.select_related('store', 'product').filter(
        quantity__lt=F('product__min_stock')
    ).order_by('quantity')
    
    # 门店筛选
    store_id = request.GET.get('store', '')
    if store_id:
        inventories = inventories.filter(store_id=store_id)
    
    stores = Store.objects.filter(is_active=True)
    
    return render(request, 'inventory/low_stock_list.html', {
        'inventories': inventories,
        'stores': stores,
        'store_id': store_id,
    })


# ==================== 库存调拨 ====================

@login_required
@manager_required
def transfer_list(request):
    """调拨单列表"""
    transfers = StockTransfer.objects.select_related(
        'from_store', 'to_store', 'created_by'
    ).all()
    
    # 状态筛选
    status = request.GET.get('status', '')
    if status:
        transfers = transfers.filter(status=status)
    
    paginator = Paginator(transfers, 20)
    page = request.GET.get('page', 1)
    transfers = paginator.get_page(page)
    
    return render(request, 'inventory/transfer_list.html', {
        'transfers': transfers,
        'status': status,
    })


@login_required
@manager_required
def transfer_create(request):
    """创建调拨单"""
    stores = Store.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    if request.method == 'POST':
        from_store_id = request.POST.get('from_store')
        to_store_id = request.POST.get('to_store')
        remark = request.POST.get('remark', '')
        
        if from_store_id == to_store_id:
            messages.error(request, '调出和调入门店不能相同')
            return redirect('inventory:transfer_create')
        
        from_store = get_object_or_404(Store, pk=from_store_id)
        to_store = get_object_or_404(Store, pk=to_store_id)
        
        with transaction.atomic():
            # 创建调拨单
            transfer = StockTransfer.objects.create(
                transfer_no=StockTransfer.generate_transfer_no(),
                from_store=from_store,
                to_store=to_store,
                remark=remark,
                created_by=request.user
            )
            
            # 添加调拨明细
            product_ids = request.POST.getlist('product_id')
            quantities = request.POST.getlist('quantity')
            
            for product_id, quantity in zip(product_ids, quantities):
                if product_id and quantity:
                    quantity = int(quantity)
                    if quantity > 0:
                        product = Product.objects.get(pk=product_id)
                        
                        # 检查库存是否充足
                        current_stock = Inventory.get_stock(from_store, product)
                        if quantity > current_stock:
                            messages.warning(
                                request, 
                                f'{product.name} 库存不足（当前:{current_stock}，申请:{quantity}）'
                            )
                            quantity = current_stock
                        
                        if quantity > 0:
                            StockTransferItem.objects.create(
                                transfer=transfer,
                                product=product,
                                quantity=quantity
                            )
        
        messages.success(request, f'调拨单 {transfer.transfer_no} 创建成功')
        return redirect('inventory:transfer_detail', pk=transfer.pk)
    
    return render(request, 'inventory/transfer_form.html', {
        'stores': stores,
        'products': products,
        'title': '新建调拨单'
    })


@login_required
@manager_required
def transfer_detail(request, pk):
    """调拨单详情"""
    transfer = get_object_or_404(
        StockTransfer.objects.select_related(
            'from_store', 'to_store', 'created_by', 'approved_by'
        ).prefetch_related('items__product'),
        pk=pk
    )
    
    return render(request, 'inventory/transfer_detail.html', {
        'transfer': transfer
    })


@login_required
@manager_required
def transfer_approve(request, pk):
    """审核调拨单"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if transfer.status != 'pending':
        messages.error(request, '只能审核待审核的调拨单')
        return redirect('inventory:transfer_detail', pk=pk)
    
    # 检查库存
    for item in transfer.items.all():
        current_stock = Inventory.get_stock(transfer.from_store, item.product)
        if item.quantity > current_stock:
            messages.error(
                request, 
                f'{item.product.name} 库存不足（当前:{current_stock}，申请:{item.quantity}）'
            )
            return redirect('inventory:transfer_detail', pk=pk)
    
    transfer.status = 'approved'
    transfer.approved_by = request.user
    transfer.approved_at = timezone.now()
    transfer.save()
    
    messages.success(request, '调拨单已审核通过')
    return redirect('inventory:transfer_detail', pk=pk)


@login_required
@manager_required
def transfer_execute(request, pk):
    """执行调拨"""
    transfer = get_object_or_404(
        StockTransfer.objects.prefetch_related('items__product'),
        pk=pk
    )
    
    if transfer.status != 'approved':
        messages.error(request, '只能执行已审核的调拨单')
        return redirect('inventory:transfer_detail', pk=pk)
    
    with transaction.atomic():
        for item in transfer.items.all():
            # 锁定库存记录
            from_inventory = Inventory.objects.select_for_update().get(
                store=transfer.from_store,
                product=item.product
            )
            
            if from_inventory.quantity < item.quantity:
                messages.error(
                    request, 
                    f'{item.product.name} 库存不足'
                )
                return redirect('inventory:transfer_detail', pk=pk)
            
            # 调出门店减少库存
            before_qty = from_inventory.quantity
            from_inventory.quantity -= item.quantity
            from_inventory.save()
            
            StockMovement.objects.create(
                store=transfer.from_store,
                product=item.product,
                movement_type='transfer_out',
                quantity=-item.quantity,
                before_quantity=before_qty,
                after_quantity=from_inventory.quantity,
                reference_no=transfer.transfer_no,
                operator=request.user,
                remark=f'调拨至 {transfer.to_store.name}'
            )
            
            # 调入门店增加库存
            to_inventory = Inventory.update_stock(
                transfer.to_store, 
                item.product, 
                item.quantity
            )
            
            StockMovement.objects.create(
                store=transfer.to_store,
                product=item.product,
                movement_type='transfer_in',
                quantity=item.quantity,
                before_quantity=to_inventory.quantity - item.quantity,
                after_quantity=to_inventory.quantity,
                reference_no=transfer.transfer_no,
                operator=request.user,
                remark=f'从 {transfer.from_store.name} 调入'
            )
        
        transfer.status = 'completed'
        transfer.completed_at = timezone.now()
        transfer.save()
    
    messages.success(request, '调拨执行成功')
    return redirect('inventory:transfer_detail', pk=pk)


@login_required
@manager_required
def transfer_cancel(request, pk):
    """取消调拨单"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if transfer.status not in ['pending', 'approved']:
        messages.error(request, '只能取消待审核或已审核的调拨单')
        return redirect('inventory:transfer_detail', pk=pk)
    
    transfer.status = 'cancelled'
    transfer.save()
    
    messages.success(request, '调拨单已取消')
    return redirect('inventory:transfer_detail', pk=pk)


# ==================== 库存盘点 ====================

@login_required
@manager_required
def check_list(request):
    """盘点单列表"""
    checks = StockCheck.objects.select_related('store', 'created_by').all()
    
    # 状态筛选
    status = request.GET.get('status', '')
    if status:
        checks = checks.filter(status=status)
    
    paginator = Paginator(checks, 20)
    page = request.GET.get('page', 1)
    checks = paginator.get_page(page)
    
    return render(request, 'inventory/check_list.html', {
        'checks': checks,
        'status': status,
    })


@login_required
@manager_required
def check_create(request):
    """创建盘点单"""
    stores = Store.objects.filter(is_active=True)
    
    if request.method == 'POST':
        store_id = request.POST.get('store')
        store = get_object_or_404(Store, pk=store_id)
        remark = request.POST.get('remark', '')
        
        with transaction.atomic():
            # 生成盘点单号
            date_str = timezone.now().strftime('%Y%m%d')
            import random
            check_no = f"CK{date_str}{random.randint(1000, 9999)}"
            
            # 创建盘点单
            check = StockCheck.objects.create(
                check_no=check_no,
                store=store,
                remark=remark,
                created_by=request.user
            )
            
            # 生成盘点明细（所有有库存的商品）
            inventories = Inventory.objects.filter(
                store=store,
                quantity__gt=0
            ).select_related('product')
            
            for inv in inventories:
                StockCheckItem.objects.create(
                    check=check,
                    product=inv.product,
                    system_quantity=inv.quantity,
                    actual_quantity=inv.quantity,  # 默认等于系统库存
                    difference=0
                )
        
        messages.success(request, f'盘点单 {check.check_no} 创建成功')
        return redirect('inventory:check_detail', pk=check.pk)
    
    return render(request, 'inventory/check_form.html', {
        'stores': stores,
    })


@login_required
@manager_required
def check_detail(request, pk):
    """盘点单详情"""
    check = get_object_or_404(
        StockCheck.objects.select_related('store', 'created_by')
        .prefetch_related('items__product'),
        pk=pk
    )
    
    return render(request, 'inventory/check_detail.html', {
        'check': check
    })


@login_required
@manager_required
def check_update(request, pk):
    """更新盘点数量"""
    check = get_object_or_404(StockCheck, pk=pk)
    
    if check.status not in ['draft', 'checking']:
        messages.error(request, '只能更新草稿或盘点中的盘点单')
        return redirect('inventory:check_detail', pk=pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            check.status = 'checking'
            check.save()
            
            for item in check.items.all():
                actual_qty = request.POST.get(f'actual_{item.pk}')
                if actual_qty is not None:
                    item.actual_quantity = int(actual_qty)
                    item.save()
        
        messages.success(request, '盘点数量已更新')
    
    return redirect('inventory:check_detail', pk=pk)


@login_required
@manager_required
def check_complete(request, pk):
    """完成盘点"""
    check = get_object_or_404(
        StockCheck.objects.prefetch_related('items__product'),
        pk=pk
    )
    
    if check.status not in ['checking']:
        messages.error(request, '只能完成盘点中的盘点单')
        return redirect('inventory:check_detail', pk=pk)
    
    with transaction.atomic():
        for item in check.items.all():
            if item.difference != 0:
                # 更新库存
                inventory = Inventory.objects.select_for_update().get(
                    store=check.store,
                    product=item.product
                )
                
                before_qty = inventory.quantity
                inventory.quantity = item.actual_quantity
                inventory.save()
                
                # 记录库存变动
                StockMovement.objects.create(
                    store=check.store,
                    product=item.product,
                    movement_type='adjust',
                    quantity=item.difference,
                    before_quantity=before_qty,
                    after_quantity=item.actual_quantity,
                    reference_no=check.check_no,
                    operator=request.user,
                    remark=f'盘点调整: {item.remark or "无备注"}'
                )
        
        check.status = 'completed'
        check.completed_at = timezone.now()
        check.save()
    
    messages.success(request, '盘点已完成，库存已调整')
    return redirect('inventory:check_detail', pk=pk)


# ==================== API ====================

@login_required
def api_product_stock(request, store_id, product_id):
    """获取商品库存 API"""
    from inventory.models import Store, Product
    store = Store.objects.get(pk=store_id)
    product = Product.objects.get(pk=product_id)
    stock = Inventory.get_stock(store, product)
    return JsonResponse({'stock': stock})


@login_required
def api_product_search(request):
    """商品搜索 API"""
    keyword = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=keyword) | Q(barcode__icontains=keyword),
        is_active=True
    )[:20]
    
    return JsonResponse({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'barcode': p.barcode,
                'price': str(p.sale_price),
            }
            for p in products
        ]
    })


