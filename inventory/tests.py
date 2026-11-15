from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from decimal import Decimal
import threading

from .models import Warehouse, Store, Product, Inventory, StockMovement


class InventoryModelTest(TestCase):
    """库存模型测试"""
    
    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name='测试仓库',
            code='WH001',
            location='测试地址'
        )
        self.store = Store.objects.create(
            name='测试门店',
            code='S001',
            address='测试地址',
            warehouse=self.warehouse
        )
        self.product = Product.objects.create(
            name='测试商品',
            barcode='BC000001',
            cost_price=Decimal('10.00'),
            sale_price=Decimal('20.00'),
            min_stock=10
        )
    
    def test_get_stock_exists(self):
        """测试获取存在的库存"""
        Inventory.objects.create(
            store=self.store,
            product=self.product,
            quantity=50
        )
        
        stock = Inventory.get_stock(self.store, self.product)
        self.assertEqual(stock, 50)
    
    def test_get_stock_not_exists(self):
        """测试获取不存在的库存"""
        stock = Inventory.get_stock(self.store, self.product)
        self.assertEqual(stock, 0)
    
    def test_update_stock(self):
        """测试更新库存"""
        # 初始库存
        inventory = Inventory.update_stock(self.store, self.product, 100)
        self.assertEqual(inventory.quantity, 100)
        
        # 增加库存
        inventory = Inventory.update_stock(self.store, self.product, 20)
        self.assertEqual(inventory.quantity, 120)
        
        # 减少库存
        inventory = Inventory.update_stock(self.store, self.product, -30)
        self.assertEqual(inventory.quantity, 90)
    
    def test_is_low_stock(self):
        """测试低库存检测"""
        inventory = Inventory.objects.create(
            store=self.store,
            product=self.product,
            quantity=5
        )
        
        self.assertTrue(inventory.is_low_stock())
        
        inventory.quantity = 15
        inventory.save()
        
        self.assertFalse(inventory.is_low_stock())


class ConcurrentInventoryTest(TransactionTestCase):
    """并发库存测试"""
    
    def setUp(self):
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
        self.inventory = Inventory.objects.create(
            store=self.store, product=self.product, quantity=100
        )
    
    def test_concurrent_deduct_no_oversell(self):
        """测试并发扣减不会超卖"""
        from django.db import transaction
        
        success_count = 0
        lock = threading.Lock()
        
        def deduct():
            nonlocal success_count
            try:
                with transaction.atomic():
                    inv = Inventory.objects.select_for_update().get(
                        store=self.store, product=self.product
                    )
                    if inv.quantity >= 2:
                        inv.quantity -= 2
                        inv.save()
                        with lock:
                            success_count += 1
            except Exception:
                pass
        
        # 50个线程并发扣减
        threads = [threading.Thread(target=deduct) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.inventory.refresh_from_db()
        
        # 验证：成功扣减 * 2 + 剩余 = 100
        self.assertEqual(success_count * 2 + self.inventory.quantity, 100)
        # 验证：没有超卖
        self.assertGreaterEqual(self.inventory.quantity, 0)