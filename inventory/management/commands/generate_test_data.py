from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from datetime import timedelta

from faker import Faker

from users.models import Employee
from inventory.models import Warehouse, Store, Category, Product, Inventory, StockMovement
from purchase.models import Supplier, PurchaseOrder, PurchaseOrderItem
from sales.models import Member, Sale, SaleItem, PointsRecord


fake = Faker('zh_CN')


class Command(BaseCommand):
    help = '生成测试数据'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--stores',
            type=int,
            default=480,
            help='门店数量（默认480）'
        )
        parser.add_argument(
            '--products',
            type=int,
            default=10000,
            help='商品数量（默认10000）'
        )
        parser.add_argument(
            '--members',
            type=int,
            default=5000,
            help='会员数量（默认5000）'
        )
        parser.add_argument(
            '--sales-days',
            type=int,
            default=90,
            help='生成多少天的销售数据（默认90）'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空现有数据'
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        self.stdout.write('开始生成测试数据...')
        
        with transaction.atomic():
            # 1. 创建仓库
            warehouses = self.create_warehouses()
            self.stdout.write(f'  创建了 {len(warehouses)} 个仓库')
            
            # 2. 创建门店
            stores = self.create_stores(warehouses, options['stores'])
            self.stdout.write(f'  创建了 {len(stores)} 个门店')
            
            # 3. 创建商品分类和商品
            categories = self.create_categories()
            products = self.create_products(categories, options['products'])
            self.stdout.write(f'  创建了 {len(products)} 个商品')
            
            # 4. 创建供应商
            suppliers = self.create_suppliers()
            self.stdout.write(f'  创建了 {len(suppliers)} 个供应商')
            
            # 5. 创建库存
            self.create_inventory(stores, products)
            self.stdout.write(f'  创建了库存记录')
            
            # 6. 创建会员
            members = self.create_members(options['members'])
            self.stdout.write(f'  创建了 {len(members)} 个会员')
            
            # 7. 创建员工
            employees = self.create_employees(stores)
            self.stdout.write(f'  创建了 {len(employees)} 个员工')
            
            # 8. 生成历史销售数据
            self.create_sales(stores, products, members, options['sales_days'])
            self.stdout.write(f'  生成了 {options["sales_days"]} 天的销售数据')
        
        self.stdout.write(self.style.SUCCESS('测试数据生成完成！'))
    
    def clear_data(self):
        """清空数据"""
        self.stdout.write('清空现有数据...')
        
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        PointsRecord.objects.all().delete()
        Member.objects.all().delete()
        
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        Supplier.objects.all().delete()
        
        StockMovement.objects.all().delete()
        Inventory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        
        Employee.objects.all().delete()
        Store.objects.all().delete()
        Warehouse.objects.all().delete()
        
        # 保留超级用户
        User.objects.filter(is_superuser=False).delete()
    
    def create_warehouses(self):
        """创建仓库"""
        regions = ['华北', '华东', '华南', '华中', '西南', '西北', '东北']
        warehouses = []
        
        for i, region in enumerate(regions, 1):
            warehouse = Warehouse.objects.create(
                name=f'{region}仓库',
                code=f'WH{i:03d}',
                location=f'{fake.city()}市{fake.street_address()}',
                contact=fake.name(),
                phone=fake.phone_number()
            )
            warehouses.append(warehouse)
        
        return warehouses
    
    def create_stores(self, warehouses, count):
        """创建门店"""
        stores = []
        stores_per_warehouse = count // len(warehouses)
        
        for i in range(count):
            warehouse = warehouses[i // stores_per_warehouse] if i // stores_per_warehouse < len(warehouses) else warehouses[-1]
            
            store = Store.objects.create(
                name=f'{fake.city()}第{(i % 100) + 1}门店',
                code=f'S{i+1:04d}',
                address=f'{fake.city()}市{fake.street_address()}',
                warehouse=warehouse,
                contact=fake.name(),
                phone=fake.phone_number()
            )
            stores.append(store)
        
        return stores
    
    def create_categories(self):
        """创建商品分类"""
        main_categories = [
            '文学小说', '人文社科', '经济管理', '科技科普',
            '少儿童书', '教育考试', '生活休闲', '艺术设计'
        ]
        
        categories = []
        
        for name in main_categories:
            category = Category.objects.create(name=name)
            categories.append(category)
            
            # 创建子分类
            if name == '文学小说':
                subs = ['中国文学', '外国文学', '青春文学', '武侠玄幻']
            elif name == '人文社科':
                subs = ['历史', '哲学', '心理学', '社会学']
            elif name == '经济管理':
                subs = ['投资理财', '管理学', '市场营销', '创业']
            elif name == '科技科普':
                subs = ['计算机', '自然科学', '工程技术', '医学健康']
            elif name == '少儿童书':
                subs = ['绘本', '科普百科', '儿童文学', '启蒙认知']
            elif name == '教育考试':
                subs = ['中小学教辅', '外语学习', '考试用书', '大学教材']
            elif name == '生活休闲':
                subs = ['烹饪美食', '旅游地图', '运动健身', '家居园艺']
            else:  # 艺术设计
                subs = ['绘画', '书法', '摄影', '设计']
            
            for sub_name in subs:
                sub_category = Category.objects.create(name=sub_name, parent=category)
                categories.append(sub_category)
        
        return categories
    
    def create_products(self, categories, count):
        """创建商品"""
        # 只使用子分类
        sub_categories = [c for c in categories if c.parent is not None]
        
        publishers = ['人民文学出版社', '中信出版社', '机械工业出版社', '电子工业出版社',
                     '清华大学出版社', '北京大学出版社', '上海文艺出版社', '浙江人民出版社']
        
        products = []
        
        for i in range(count):
            category = random.choice(sub_categories)
            cost_price = Decimal(str(random.randint(10, 50)))
            sale_price = cost_price * Decimal('1.5') + Decimal(str(random.randint(0, 20)))
            
            product = Product(
                name=f'{fake.sentence(nb_words=3)}',
                barcode=f'978{random.randint(1000000000, 9999999999)}',
                isbn=f'978-7-{random.randint(100, 999)}-{random.randint(10000, 99999)}-{random.randint(0, 9)}',
                category=category,
                author=fake.name(),
                publisher=random.choice(publishers),
                cost_price=cost_price,
                sale_price=sale_price.quantize(Decimal('0.01')),
                min_stock=random.randint(5, 20)
            )
            products.append(product)
        
        Product.objects.bulk_create(products, batch_size=1000)
        return list(Product.objects.all())
    
    def create_suppliers(self):
        """创建供应商"""
        supplier_names = [
            '新华书店总店', '当当图书', '京东图书', '博库网',
            '文轩网', '中国图书网', '亚马逊图书', '淘书网'
        ]
        
        suppliers = []
        
        for i, name in enumerate(supplier_names, 1):
            supplier = Supplier.objects.create(
                name=name,
                code=f'SUP{i:03d}',
                contact=fake.name(),
                phone=fake.phone_number(),
                email=fake.email(),
                address=f'{fake.city()}市{fake.street_address()}'
            )
            suppliers.append(supplier)
        
        return suppliers
    
    def create_inventory(self, stores, products):
        """创建库存"""
        inventories = []
        
        for store in stores:
            # 每个门店随机有 30%-70% 的商品
            store_products = random.sample(products, int(len(products) * random.uniform(0.3, 0.7)))
            
            for product in store_products:
                inventory = Inventory(
                    store=store,
                    product=product,
                    quantity=random.randint(0, 200)
                )
                inventories.append(inventory)
        
        Inventory.objects.bulk_create(inventories, batch_size=5000)
    
    def create_members(self, count):
        """创建会员"""
        members = []
        
        for i in range(count):
            member = Member(
                member_no=f'M{timezone.now().strftime("%Y%m%d")}{i+1:04d}',
                name=fake.name(),
                phone=fake.phone_number(),
                email=fake.email() if random.random() > 0.5 else '',
                points=random.randint(0, 5000),
                total_amount=Decimal(str(random.randint(0, 10000)))
            )
            members.append(member)
        
        Member.objects.bulk_create(members, batch_size=1000)
        return list(Member.objects.all())
    
    def create_employees(self, stores):
        """创建员工"""
        employees = []
        
        # 为每个门店创建员工
        for store in stores[:50]:  # 只为前50个门店创建详细员工
            # 店长
            user = User.objects.create_user(
                username=f'manager_{store.code}',
                password='password123',
                first_name=fake.name()
            )
            employee = Employee.objects.create(
                user=user,
                role='manager',
                store=store,
                phone=fake.phone_number()
            )
            employees.append(employee)
            
            # 收银员
            for j in range(2):
                user = User.objects.create_user(
                    username=f'cashier_{store.code}_{j+1}',
                    password='password123',
                    first_name=fake.name()
                )
                employee = Employee.objects.create(
                    user=user,
                    role='cashier',
                    store=store,
                    phone=fake.phone_number()
                )
                employees.append(employee)
        
        return employees
    
    def create_sales(self, stores, products, members, days):
        """生成历史销售数据"""
        today = timezone.now()
        sales = []
        sale_items = []
        
        # 为每一天生成销售数据
        for day_offset in range(days, 0, -1):
            sale_date = today - timedelta(days=day_offset)
            
            # 每个门店每天 5-20 笔销售
            for store in stores[:100]:  # 只为前100个门店生成详细数据
                daily_sales = random.randint(5, 20)
                
                for _ in range(daily_sales):
                    # 随机选择会员（30%概率）
                    member = random.choice(members) if random.random() > 0.7 else None
                    
                    # 创建销售单
                    total_amount = Decimal('0')
                    discount_amount = Decimal('0')
                    
                    # 周三88折
                    is_wednesday = sale_date.weekday() == 2
                    
                    sale_time = sale_date + timedelta(hours=random.randint(9, 21), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
                    sale = Sale(
                        order_no=f'S{sale_time.strftime("%Y%m%d%H%M%S")}{store.id:04d}{random.randint(1000, 9999)}',
                        store=store,
                        member=member,
                        status='paid',
                        payment_method=random.choice(['cash', 'wechat', 'alipay']),
                        created_at=sale_time,
                        paid_at=sale_time
                    )
                    
                    # 每笔销售 1-5 个商品
                    item_count = random.randint(1, 5)
                    sale_products = random.sample(products, min(item_count, len(products)))
                    
                    items_for_this_sale = []
                    for product in sale_products:
                        quantity = random.randint(1, 3)
                        price = product.sale_price
                        
                        item = SaleItem(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            price=price,
                            cost_price=product.cost_price
                        )
                        items_for_this_sale.append(item)
                        total_amount += price * quantity
                    
                    # 计算折扣
                    if is_wednesday:
                        discount_amount = total_amount * Decimal('0.12')
                        final_amount = total_amount * Decimal('0.88')
                    else:
                        final_amount = total_amount
                    
                    sale.total_amount = total_amount
                    sale.discount_amount = discount_amount.quantize(Decimal('0.01'))
                    sale.final_amount = final_amount.quantize(Decimal('0.01'))
                    sale.points_earned = int(final_amount) if member else 0
                    
                    sales.append(sale)
                    sale_items.extend(items_for_this_sale)
            
            # 每处理 10 天输出进度
            if day_offset % 10 == 0:
                self.stdout.write(f'  处理第 {days - day_offset + 1}/{days} 天')
        
        # 批量创建
        self.stdout.write('  批量插入销售数据...')
        Sale.objects.bulk_create(sales, batch_size=5000)
        
        # 重新获取销售记录以获取ID
        sales_dict = {s.order_no: s for s in Sale.objects.all()}
        
        for item in sale_items:
            if item.sale.order_no in sales_dict:
                item.sale = sales_dict[item.sale.order_no]
        
        SaleItem.objects.bulk_create(sale_items, batch_size=10000)
