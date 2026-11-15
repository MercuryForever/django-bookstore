from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Supplier(models.Model):
    """供应商模型"""
    
    name = models.CharField(max_length=100, verbose_name='供应商名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='供应商编码')
    contact = models.CharField(max_length=50, verbose_name='联系人')
    phone = models.CharField(max_length=20, verbose_name='联系电话')
    email = models.EmailField(blank=True, verbose_name='邮箱')
    address = models.CharField(max_length=200, blank=True, verbose_name='地址')
    bank_name = models.CharField(max_length=100, blank=True, verbose_name='开户银行')
    bank_account = models.CharField(max_length=50, blank=True, verbose_name='银行账号')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '供应商'
        verbose_name_plural = '供应商'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class PurchaseOrder(models.Model):
    """采购订单"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('approved', '已审核'),
        ('receiving', '收货中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    order_no = models.CharField(max_length=50, unique=True, verbose_name='采购单号')
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name='供应商'
    )
    warehouse = models.ForeignKey(
        'inventory.Warehouse', 
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name='入库仓库'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name='状态'
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='总金额'
    )
    expected_date = models.DateField(null=True, blank=True, verbose_name='预计到货日期')
    remark = models.TextField(blank=True, verbose_name='备注')
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_purchase_orders',
        verbose_name='创建人'
    )
    approved_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_purchase_orders',
        verbose_name='审核人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '采购订单'
        verbose_name_plural = '采购订单'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_no} - {self.supplier.name}"
    
    @staticmethod
    def generate_order_no():
        """生成采购单号"""
        from django.utils import timezone
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"PO{date_str}{random_str}"
    
    def calculate_total(self):
        """计算订单总金额"""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


class PurchaseOrderItem(models.Model):
    """采购订单明细"""
    
    order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='采购订单'
    )
    product = models.ForeignKey(
        'inventory.Product', 
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='采购数量'
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='采购单价'
    )
    received_quantity = models.IntegerField(default=0, verbose_name='已收货数量')
    
    class Meta:
        verbose_name = '采购订单明细'
        verbose_name_plural = '采购订单明细'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def subtotal(self):
        """小计金额"""
        return self.quantity * self.price
    
    @property
    def pending_quantity(self):
        """待收货数量"""
        return self.quantity - self.received_quantity


class PurchaseReceive(models.Model):
    """采购收货单"""
    
    receive_no = models.CharField(max_length=50, unique=True, verbose_name='收货单号')
    order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.PROTECT,
        related_name='receives',
        verbose_name='采购订单'
    )
    store = models.ForeignKey(
        'inventory.Store', 
        on_delete=models.PROTECT,
        verbose_name='入库门店'
    )
    remark = models.TextField(blank=True, verbose_name='备注')
    received_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='收货人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收货时间')
    
    class Meta:
        verbose_name = '收货单'
        verbose_name_plural = '收货单'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.receive_no}"
    
    @staticmethod
    def generate_receive_no():
        """生成收货单号"""
        from django.utils import timezone
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"RV{date_str}{random_str}"


class PurchaseReceiveItem(models.Model):
    """收货单明细"""
    
    receive = models.ForeignKey(
        PurchaseReceive, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='收货单'
    )
    order_item = models.ForeignKey(
        PurchaseOrderItem, 
        on_delete=models.PROTECT,
        verbose_name='采购订单明细'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='收货数量'
    )
    
    class Meta:
        verbose_name = '收货单明细'
        verbose_name_plural = '收货单明细'
    
    def __str__(self):
        return f"{self.order_item.product.name} x {self.quantity}"