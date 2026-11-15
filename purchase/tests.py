from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from inventory.models import Warehouse, Store, Product, Inventory


class PurchaseOrderTest(TestCase):
    """采购订单测试"""
    
    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name='测试仓库', code='WH001', location='测试'
        )
        self.supplier = Supplier.objects.create(
            name='测试供应商', code='SUP001', contact='联系人', phone='13800138000'
        )
        self.product = Product.objects.create(
            name='测试商品', barcode='BC000001',
            cost_price=Decimal('10'), sale_price=Decimal('20')
        )
        self.user = User.objects.create_user('testuser', password='pass123')
    
    def test_generate_order_no(self):
        """测试生成采购单号"""
        order_no = PurchaseOrder.generate_order_no()
        
        self.assertTrue(order_no.startswith('PO'))
    
    def test_calculate_total(self):
        """测试计算订单总金额"""
        order = PurchaseOrder.objects.create(
            order_no='PO202401010001',
            supplier=self.supplier,
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        PurchaseOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=10,
            price=Decimal('15.00')
        )
        PurchaseOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=5,
            price=Decimal('12.00')
        )
        
        total = order.calculate_total()
        
        self.assertEqual(total, Decimal('210.00'))  # 10*15 + 5*12
        self.assertEqual(order.total_amount, Decimal('210.00'))
    
    def test_item_subtotal(self):
        """测试采购项小计"""
        order = PurchaseOrder.objects.create(
            order_no='PO202401010001',
            supplier=self.supplier,
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        item = PurchaseOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=10,
            price=Decimal('15.00')
        )
        
        self.assertEqual(item.subtotal, Decimal('150.00'))