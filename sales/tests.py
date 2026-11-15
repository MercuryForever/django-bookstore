from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import json

from .models import Member, Sale, SaleItem, PointsRecord
from inventory.models import Warehouse, Store, Product, Inventory
from users.models import Employee


class MemberModelTest(TestCase):
    """会员模型测试"""
    
    def test_generate_member_no(self):
        """测试生成会员卡号"""
        member_no = Member.generate_member_no()
        
        self.assertTrue(member_no.startswith('M'))
        self.assertEqual(len(member_no), 13)  # M + 8位日期 + 4位随机
    
    def test_add_points(self):
        """测试增加积分"""
        member = Member.objects.create(
            member_no='M202401010001',
            name='测试会员',
            phone='13800138000',
            points=0,
            total_amount=Decimal('0')
        )
        
        points_added = member.add_points(Decimal('100.50'))
        
        self.assertEqual(points_added, 100)  # 1元=1积分，向下取整
        self.assertEqual(member.points, 100)
        self.assertEqual(member.total_amount, Decimal('100.50'))


class SaleModelTest(TestCase):
    """销售模型测试"""
    
    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name='测试仓库', code='WH001', location='测试'
        )
        self.store = Store.objects.create(
            name='测试门店', code='S001', address='测试', warehouse=self.warehouse
        )
        self.member = Member.objects.create(
            member_no='M202401010001',
            name='测试会员',
            phone='13800138000'
        )
    
    def test_generate_order_no(self):
        """测试生成订单号"""
        order_no = Sale.generate_order_no()
        
        self.assertTrue(order_no.startswith('S'))
    
    def test_calculate_discount_wednesday(self):
        """测试周三折扣计算"""
        sale = Sale.objects.create(
            order_no='S20240101001',
            store=self.store,
            total_amount=Decimal('100.00')
        )
        
        # 模拟周三
        from unittest.mock import patch
        import datetime
        
        wednesday = datetime.datetime(2024, 1, 3, 12, 0)  # 周三
        with patch('django.utils.timezone.now', return_value=wednesday):
            sale.calculate_discount()
        
        self.assertEqual(sale.discount_amount, Decimal('12.00'))
        self.assertEqual(sale.final_amount, Decimal('88.00'))
    
    def test_calculate_discount_not_wednesday(self):
        """测试非周三无折扣"""
        sale = Sale.objects.create(
            order_no='S20240101001',
            store=self.store,
            total_amount=Decimal('100.00')
        )
        
        from unittest.mock import patch
        import datetime
        
        monday = datetime.datetime(2024, 1, 1, 12, 0)  # 周一
        with patch('django.utils.timezone.now', return_value=monday):
            sale.calculate_discount()
        
        self.assertEqual(sale.discount_amount, Decimal('0.00'))
        self.assertEqual(sale.final_amount, Decimal('100.00'))


class POSCheckoutTest(TestCase):
    """收银结算测试"""
    
    def setUp(self):
        self.client = Client()
        
        self.warehouse = Warehouse.objects.create(
            name='测试仓库', code='WH001', location='测试'
        )
        self.store = Store.objects.create(
            name='测试门店', code='S001', address='测试', warehouse=self.warehouse
        )
        self.product = Product.objects.create(
            name='测试商品', barcode='BC000001',
            cost_price=Decimal('10'), sale_price=Decimal('20')
        )
        Inventory.objects.create(
            store=self.store, product=self.product, quantity=100
        )
        
        self.user = User.objects.create_user('cashier', password='pass123')
        Employee.objects.create(user=self.user, role='cashier', store=self.store)
    
    def test_checkout_success(self):
        """测试结算成功"""
        self.client.login(username='cashier', password='pass123')
        
        response = self.client.post(
            '/sales/pos/checkout/',
            data=json.dumps({
                'store_id': self.store.pk,
                'items': [
                    {'product_id': self.product.pk, 'quantity': 2, 'price': '20.00'}
                ],
                'payment_method': 'cash'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # 验证库存扣减
        inventory = Inventory.objects.get(store=self.store, product=self.product)
        self.assertEqual(inventory.quantity, 98)
    
    def test_checkout_insufficient_stock(self):
        """测试库存不足"""
        self.client.login(username='cashier', password='pass123')
        
        response = self.client.post(
            '/sales/pos/checkout/',
            data=json.dumps({
                'store_id': self.store.pk,
                'items': [
                    {'product_id': self.product.pk, 'quantity': 200, 'price': '20.00'}
                ],
                'payment_method': 'cash'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('库存不足', data['error'])