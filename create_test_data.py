import os
import django
from decimal import Decimal

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from users.models import Employee
from inventory.models import Store, Category, Product, Inventory
from sales.models import Sale, SaleItem

# 创建测试用户
try:
    user = User.objects.create_user(
        username='manager_S0001',
        password='password123',
        first_name='测试管理员'
    )
    print('用户创建成功')
except Exception as e:
    print(f'用户创建失败或已存在: {e}')
    user = User.objects.get(username='manager_S0001')

# 创建测试门店
try:
    store = Store.objects.create(
        name='测试门店',
        code='S0001',
        address='测试地址',
        contact='测试联系人',
        phone='1234567890'
    )
    print('门店创建成功')
except Exception as e:
    print(f'门店创建失败或已存在: {e}')
    store = Store.objects.get(code='S0001')

# 为用户关联门店
try:
    employee = Employee.objects.create(
        user=user,
        store=store,
        role='manager',
        phone='1234567890'
    )
    print('员工关联成功')
except Exception as e:
    print(f'员工关联失败或已存在: {e}')

# 创建商品分类
try:
    category = Category.objects.create(name='测试分类')
    print('分类创建成功')
except Exception as e:
    print(f'分类创建失败或已存在: {e}')
    category = Category.objects.get(name='测试分类')

# 创建测试商品
if Product.objects.count() < 5:
    for i in range(5):
        product = Product.objects.create(
            name=f'测试商品{i+1}',
            barcode=f'1234567890{i+1}',
            isbn=f'978-7-123-45678-{i+1}',
            category=category,
            author='测试作者',
            publisher='测试出版社',
            cost_price=Decimal('10.00'),
            sale_price=Decimal(str(20.00 + i)),
            min_stock=5
        )
        # 创建库存
        Inventory.objects.create(
            store=store,
            product=product,
            quantity=100
        )
    print('商品创建成功')
else:
    print('商品已存在')

# 创建测试销售记录
if Sale.objects.count() < 10:
    for i in range(10):
        # 创建销售单
        sale = Sale.objects.create(
            order_no=f'S{timezone.now().strftime("%Y%m%d%H%M%S")}{i+1:03d}',
            store=store,
            status='paid',
            payment_method='wechat',
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            created_at=timezone.now() - timezone.timedelta(days=i),
            paid_at=timezone.now() - timezone.timedelta(days=i)
        )
        
        # 创建销售明细
        products = Product.objects.all()[:3]
        total_amount = Decimal('0.00')
        for j, product in enumerate(products):
            quantity = j + 1
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                price=product.sale_price,
                cost_price=product.cost_price
            )
            total_amount += product.sale_price * quantity
        
        # 更新销售单金额
        sale.total_amount = total_amount
        sale.final_amount = total_amount
        sale.save()
    print('销售记录创建成功')
else:
    print('销售记录已存在')

print('测试数据准备完成！')
