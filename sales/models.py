from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class Member(models.Model):
    """会员模型"""
    
    # 性别选择
    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    ]
    
    member_no = models.CharField(max_length=20, unique=True, verbose_name='会员卡号')
    name = models.CharField(max_length=50, verbose_name='姓名')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name='性别')
    birth_date = models.DateField(null=True, blank=True, verbose_name='生日')
    phone = models.CharField(max_length=20, unique=True, verbose_name='手机号')
    email = models.EmailField(blank=True, verbose_name='邮箱')
    address = models.CharField(max_length=200, blank=True, verbose_name='地址')
    points = models.IntegerField(default=0, verbose_name='积分')
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='累计消费'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '会员'
        verbose_name_plural = '会员'
    
    def __str__(self):
        return f"{self.name} ({self.member_no})"
    
    @staticmethod
    def generate_member_no():
        """生成会员卡号"""
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"M{date_str}{random_str}"
    
    def add_points(self, amount):
        """增加积分（1元=1积分）"""
        points_to_add = int(amount)
        self.points += points_to_add
        self.total_amount += Decimal(str(amount))
        self.save(update_fields=['points', 'total_amount'])
        return points_to_add


class PointsRecord(models.Model):
    """积分记录"""
    
    TYPE_CHOICES = [
        ('earn', '获得'),
        ('use', '使用'),
        ('expire', '过期'),
        ('adjust', '调整'),
    ]
    
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE,
        related_name='points_records',
        verbose_name='会员'
    )
    record_type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        verbose_name='类型'
    )
    points = models.IntegerField(verbose_name='积分变动')
    balance = models.IntegerField(verbose_name='积分余额')
    reference_no = models.CharField(max_length=50, blank=True, verbose_name='关联单号')
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '积分记录'
        verbose_name_plural = '积分记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.name}: {self.points:+d}"


class Sale(models.Model):
    """销售订单"""
    
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', '现金'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('card', '银行卡'),
    ]
    
    order_no = models.CharField(max_length=50, unique=True, verbose_name='订单号')
    store = models.ForeignKey(
        'inventory.Store', 
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='门店'
    )
    member = models.ForeignKey(
        Member, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales',
        verbose_name='会员'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='状态'
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='商品总额'
    )
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='优惠金额'
    )
    final_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='实付金额'
    )
    points_earned = models.IntegerField(default=0, verbose_name='获得积分')
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        verbose_name='支付方式'
    )
    cashier = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='sales',
        verbose_name='收银员'
    )
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='支付时间')
    
    class Meta:
        verbose_name = '销售订单'
        verbose_name_plural = '销售订单'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', '-created_at']),
            models.Index(fields=['member', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.order_no}"
    
    @staticmethod
    def generate_order_no():
        """生成订单号"""
        import random
        date_str = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = str(random.randint(100, 999))
        return f"S{date_str}{random_str}"
    
    def calculate_discount(self):
        """计算折扣（周三88折）"""
        # 检查是否是周三
        if timezone.now().weekday() == 2:  # 0=周一, 2=周三
            discount_rate = Decimal('0.88')
            self.discount_amount = self.total_amount * (1 - discount_rate)
            self.final_amount = self.total_amount * discount_rate
        else:
            self.discount_amount = Decimal('0.00')
            self.final_amount = self.total_amount
        return self.final_amount
    
    def complete_payment(self, payment_method):
        """完成支付"""
        self.status = 'paid'
        self.payment_method = payment_method
        self.paid_at = timezone.now()
        
        # 计算并增加会员积分
        if self.member:
            self.points_earned = self.member.add_points(self.final_amount)
            # 记录积分
            PointsRecord.objects.create(
                member=self.member,
                record_type='earn',
                points=self.points_earned,
                balance=self.member.points,
                reference_no=self.order_no,
                remark=f'消费获得积分'
            )
        
        self.save()


class SaleItem(models.Model):
    """销售订单明细"""
    
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='销售订单'
    )
    product = models.ForeignKey(
        'inventory.Product', 
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='数量'
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='单价'
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='成本价'
    )
    
    class Meta:
        verbose_name = '销售订单明细'
        verbose_name_plural = '销售订单明细'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def subtotal(self):
        """小计金额"""
        return self.quantity * self.price
    
    @property
    def profit(self):
        """利润"""
        return self.subtotal - (self.quantity * self.cost_price)