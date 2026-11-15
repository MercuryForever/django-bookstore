from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Warehouse(models.Model):
    """仓库模型"""
    
    name = models.CharField(max_length=100, verbose_name='仓库名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='仓库编码')
    location = models.CharField(max_length=200, verbose_name='仓库地址')
    contact = models.CharField(max_length=50, blank=True, verbose_name='联系人')
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '仓库'
        verbose_name_plural = '仓库'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Store(models.Model):
    """门店模型"""
    
    name = models.CharField(max_length=100, verbose_name='门店名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='门店编码')
    address = models.CharField(max_length=200, verbose_name='门店地址')
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.PROTECT,
        related_name='stores',
        verbose_name='所属仓库'
    )
    contact = models.CharField(max_length=50, blank=True, verbose_name='联系人')
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '门店'
        verbose_name_plural = '门店'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Category(models.Model):
    """商品分类"""
    
    name = models.CharField(max_length=50, verbose_name='分类名称')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name='父分类'
    )
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    
    class Meta:
        verbose_name = '商品分类'
        verbose_name_plural = '商品分类'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    """商品模型"""
    
    name = models.CharField(max_length=200, verbose_name='商品名称')
    barcode = models.CharField(max_length=50, unique=True, verbose_name='条码')
    isbn = models.CharField(max_length=20, blank=True, verbose_name='ISBN')
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='products',
        verbose_name='分类'
    )
    author = models.CharField(max_length=100, blank=True, verbose_name='作者')
    publisher = models.CharField(max_length=100, blank=True, verbose_name='出版社')
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='成本价'
    )
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='销售价'
    )
    min_stock = models.IntegerField(default=10, verbose_name='最低库存预警')
    is_active = models.BooleanField(default=True, verbose_name='是否上架')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.barcode})"


class Inventory(models.Model):
    """库存模型 - 记录每个门店的商品库存"""
    
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name='门店'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name='商品'
    )
    quantity = models.IntegerField(default=0, verbose_name='库存数量')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '库存'
        verbose_name_plural = '库存'
        unique_together = ['store', 'product']
        indexes = [
            models.Index(fields=['store', 'product']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.product.name}: {self.quantity}"
    
    @classmethod
    def get_stock(cls, store, product):
        """获取指定门店商品的库存数量"""
        try:
            return cls.objects.get(store=store, product=product).quantity
        except cls.DoesNotExist:
            return 0
    
    @classmethod
    def update_stock(cls, store, product, quantity_change):
        """更新库存数量（正数增加，负数减少）"""
        inventory, created = cls.objects.get_or_create(
            store=store, 
            product=product,
            defaults={'quantity': 0}
        )
        inventory.quantity += quantity_change
        inventory.save()
        return inventory
    
    def is_low_stock(self):
        """是否低于安全库存"""
        return self.quantity < self.product.min_stock


class StockMovement(models.Model):
    """库存变动记录"""
    
    MOVEMENT_TYPE_CHOICES = [
        ('purchase_in', '采购入库'),
        ('sale_out', '销售出库'),
        ('transfer_out', '调拨出库'),
        ('transfer_in', '调拨入库'),
        ('adjust', '盘点调整'),
        ('return_in', '退货入库'),
    ]
    
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='门店'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='商品'
    )
    movement_type = models.CharField(
        max_length=20, 
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name='变动类型'
    )
    quantity = models.IntegerField(verbose_name='变动数量')  # 正数入库，负数出库
    before_quantity = models.IntegerField(verbose_name='变动前数量')
    after_quantity = models.IntegerField(verbose_name='变动后数量')
    reference_no = models.CharField(max_length=50, blank=True, verbose_name='关联单号')
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    operator = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='操作人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '库存变动'
        verbose_name_plural = '库存变动'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'product', '-created_at']),
            models.Index(fields=['reference_no']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.product.name}: {self.quantity:+d}"


class StockTransfer(models.Model):
    """库存调拨单"""
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已审核'),
        ('in_transit', '调拨中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    transfer_no = models.CharField(max_length=50, unique=True, verbose_name='调拨单号')
    from_store = models.ForeignKey(
        Store, 
        on_delete=models.PROTECT,
        related_name='transfers_out',
        verbose_name='调出门店'
    )
    to_store = models.ForeignKey(
        Store, 
        on_delete=models.PROTECT,
        related_name='transfers_in',
        verbose_name='调入门店'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='状态'
    )
    remark = models.TextField(blank=True, verbose_name='备注')
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_transfers',
        verbose_name='创建人'
    )
    approved_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_transfers',
        verbose_name='审核人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '调拨单'
        verbose_name_plural = '调拨单'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transfer_no}: {self.from_store.name} → {self.to_store.name}"
    
    @staticmethod
    def generate_transfer_no():
        """生成调拨单号"""
        from django.utils import timezone
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"TR{date_str}{random_str}"


class StockTransferItem(models.Model):
    """调拨单明细"""
    
    transfer = models.ForeignKey(
        StockTransfer, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='调拨单'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='数量'
    )
    
    class Meta:
        verbose_name = '调拨单明细'
        verbose_name_plural = '调拨单明细'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class StockCheck(models.Model):
    """库存盘点单"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('checking', '盘点中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    check_no = models.CharField(max_length=50, unique=True, verbose_name='盘点单号')
    store = models.ForeignKey(
        Store, 
        on_delete=models.PROTECT,
        related_name='stock_checks',
        verbose_name='门店'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name='状态'
    )
    remark = models.TextField(blank=True, verbose_name='备注')
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '盘点单'
        verbose_name_plural = '盘点单'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.check_no} - {self.store.name}"


class StockCheckItem(models.Model):
    """盘点单明细"""
    
    stock_check = models.ForeignKey(
        StockCheck, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='盘点单'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    system_quantity = models.IntegerField(verbose_name='系统库存')
    actual_quantity = models.IntegerField(verbose_name='实际库存')
    difference = models.IntegerField(verbose_name='差异数量')
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    
    class Meta:
        verbose_name = '盘点单明细'
        verbose_name_plural = '盘点单明细'
    
    def __str__(self):
        return f"{self.product.name}: 系统{self.system_quantity}, 实际{self.actual_quantity}"
    
    def save(self, *args, **kwargs):
        self.difference = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs)