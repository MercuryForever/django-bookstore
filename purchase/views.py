from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.utils import timezone

from .models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceive, PurchaseReceiveItem
from .forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet, PurchaseReceiveForm
from inventory.models import Inventory, StockMovement, Product
from users.decorators import manager_required


# ==================== 供应商管理 ====================

@login_required
@manager_required
def supplier_list(request):
    """供应商列表"""
    suppliers = Supplier.objects.all()
    
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(name__icontains=search) | suppliers.filter(code__icontains=search)
    
    paginator = Paginator(suppliers, 20)
    page = request.GET.get('page', 1)
    suppliers = paginator.get_page(page)
    
    return render(request, 'purchase/supplier_list.html', {
        'suppliers': suppliers,
        'search': search,
    })


@login_required
@manager_required
def supplier_create(request):
    """创建供应商"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '供应商创建成功')
            return redirect('purchase:supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'purchase/supplier_form.html', {
        'form': form,
        'title': '新增供应商'
    })


@login_required
@manager_required
def supplier_edit(request, pk):
    """编辑供应商"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, '供应商信息已更新')
            return redirect('purchase:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'purchase/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': '编辑供应商'
    })


# ==================== 采购订单管理 ====================

@login_required
@manager_required
def order_list(request):
    """采购订单列表"""
    orders = PurchaseOrder.objects.select_related('supplier', 'warehouse', 'created_by').all()
    
    # 状态筛选
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    # 供应商筛选
    supplier_id = request.GET.get('supplier', '')
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    
    # 日期范围
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    suppliers = Supplier.objects.filter(is_active=True)
    
    return render(request, 'purchase/order_list.html', {
        'orders': orders,
        'suppliers': suppliers,
        'status': status,
        'supplier_id': supplier_id,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
@manager_required
def order_create(request):
    """创建采购订单"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.order_no = PurchaseOrder.generate_order_no()
                order.created_by = request.user
                order.save()
                
                formset.instance = order
                formset.save()
                
                # 计算总金额
                order.calculate_total()
            
            messages.success(request, f'采购订单 {order.order_no} 创建成功')
            return redirect('purchase:order_detail', pk=order.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    
    products = Product.objects.filter(is_active=True)
    
    return render(request, 'purchase/order_form.html', {
        'form': form,
        'formset': formset,
        'products': products,
        'title': '新建采购订单'
    })


@login_required
@manager_required
def order_edit(request, pk):
    """编辑采购订单（仅草稿状态）"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if order.status != 'draft':
        messages.error(request, '只能编辑草稿状态的订单')
        return redirect('purchase:order_detail', pk=pk)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=order)
        formset = PurchaseOrderItemFormSet(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                order.calculate_total()
            
            messages.success(request, '采购订单已更新')
            return redirect('purchase:order_detail', pk=pk)
    else:
        form = PurchaseOrderForm(instance=order)
        formset = PurchaseOrderItemFormSet(instance=order)
    
    products = Product.objects.filter(is_active=True)
    
    return render(request, 'purchase/order_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'products': products,
        'title': '编辑采购订单'
    })


@login_required
@manager_required
def order_detail(request, pk):
    """采购订单详情"""
    order = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier', 'warehouse', 'created_by', 'approved_by')
        .prefetch_related('items__product', 'receives'),
        pk=pk
    )
    
    return render(request, 'purchase/order_detail.html', {
        'order': order
    })


@login_required
@manager_required
def order_submit(request, pk):
    """提交采购订单"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if order.status != 'draft':
        messages.error(request, '只能提交草稿状态的订单')
        return redirect('purchase:order_detail', pk=pk)
    
    if not order.items.exists():
        messages.error(request, '订单必须包含至少一个商品')
        return redirect('purchase:order_detail', pk=pk)
    
    order.status = 'submitted'
    order.save()
    
    messages.success(request, '采购订单已提交')
    return redirect('purchase:order_detail', pk=pk)


@login_required
@manager_required
def order_approve(request, pk):
    """审核采购订单"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if order.status != 'submitted':
        messages.error(request, '只能审核已提交的订单')
        return redirect('purchase:order_detail', pk=pk)
    
    order.status = 'approved'
    order.approved_by = request.user
    order.approved_at = timezone.now()
    order.save()
    
    messages.success(request, '采购订单已审核通过')
    return redirect('purchase:order_detail', pk=pk)


@login_required
@manager_required
def order_cancel(request, pk):
    """取消采购订单"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if order.status not in ['draft', 'submitted']:
        messages.error(request, '只能取消草稿或已提交状态的订单')
        return redirect('purchase:order_detail', pk=pk)
    
    order.status = 'cancelled'
    order.save()
    
    messages.success(request, '采购订单已取消')
    return redirect('purchase:order_detail', pk=pk)


# ==================== 入库操作 ====================

@login_required
@manager_required
def order_receive(request, pk):
    """采购入库"""
    order = get_object_or_404(
        PurchaseOrder.objects.prefetch_related('items__product'),
        pk=pk
    )
    
    if order.status not in ['approved', 'receiving']:
        messages.error(request, '只能对已审核的订单进行入库操作')
        return redirect('purchase:order_detail', pk=pk)
    
    # 获取仓库下的门店
    stores = order.warehouse.stores.filter(is_active=True)
    
    if request.method == 'POST':
        store_id = request.POST.get('store')
        store = get_object_or_404(order.warehouse.stores, pk=store_id)
        remark = request.POST.get('remark', '')
        
        with transaction.atomic():
            # 创建收货单
            receive = PurchaseReceive.objects.create(
                receive_no=PurchaseReceive.generate_receive_no(),
                order=order,
                store=store,
                remark=remark,
                received_by=request.user
            )
            
            # 处理每个商品的入库
            all_received = True
            for item in order.items.all():
                quantity_key = f'quantity_{item.pk}'
                quantity = int(request.POST.get(quantity_key, 0))
                
                if quantity > 0:
                    # 检查是否超过待收货数量
                    if quantity > item.pending_quantity:
                        quantity = item.pending_quantity
                    
                    # 创建收货明细
                    PurchaseReceiveItem.objects.create(
                        receive=receive,
                        order_item=item,
                        quantity=quantity
                    )
                    
                    # 更新采购明细的已收货数量
                    item.received_quantity += quantity
                    item.save()
                    
                    # 更新库存
                    inventory = Inventory.update_stock(store, item.product, quantity)
                    
                    # 记录库存变动
                    StockMovement.objects.create(
                        store=store,
                        product=item.product,
                        movement_type='purchase_in',
                        quantity=quantity,
                        before_quantity=inventory.quantity - quantity,
                        after_quantity=inventory.quantity,
                        reference_no=receive.receive_no,
                        operator=request.user,
                        remark=f'采购入库: {order.order_no}'
                    )
                
                # 检查是否还有待收货数量
                if item.pending_quantity > 0:
                    all_received = False
            
            # 更新订单状态
            if all_received:
                order.status = 'completed'
                order.completed_at = timezone.now()
            else:
                order.status = 'receiving'
            order.save()
        
        messages.success(request, f'入库成功，收货单号: {receive.receive_no}')
        return redirect('purchase:order_detail', pk=pk)
    
    return render(request, 'purchase/order_receive.html', {
        'order': order,
        'stores': stores,
    })