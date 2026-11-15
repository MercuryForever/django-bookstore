from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Employee
from inventory.models import Store, Warehouse


class EmployeeModelTest(TestCase):
    """员工模型测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='测试用户'
        )
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
    
    def test_create_employee(self):
        """测试创建员工"""
        employee = Employee.objects.create(
            user=self.user,
            role='cashier',
            store=self.store,
            phone='13800138000'
        )
        
        self.assertEqual(employee.user.username, 'testuser')
        self.assertEqual(employee.role, 'cashier')
        self.assertTrue(employee.is_cashier())
        self.assertFalse(employee.is_admin())
    
    def test_employee_str(self):
        """测试员工字符串表示"""
        employee = Employee.objects.create(
            user=self.user,
            role='manager',
            store=self.store
        )
        
        self.assertIn('测试用户', str(employee))
        self.assertIn('店长', str(employee))


class AuthenticationTest(TestCase):
    """认证测试"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.warehouse = Warehouse.objects.create(
            name='测试仓库', code='WH001', location='测试'
        )
        self.store = Store.objects.create(
            name='测试门店', code='S001', address='测试', warehouse=self.warehouse
        )
        self.employee = Employee.objects.create(
            user=self.user,
            role='admin',
            store=self.store
        )
    
    def test_login_success(self):
        """测试登录成功"""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 302)  # 重定向
        self.assertTrue(response.url, '/')
    
    def test_login_fail(self):
        """测试登录失败"""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)  # 停留在登录页
    
    def test_logout(self):
        """测试退出登录"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:logout'))
        
        self.assertEqual(response.status_code, 302)


class PermissionTest(TestCase):
    """权限测试"""
    
    def setUp(self):
        self.client = Client()
        self.warehouse = Warehouse.objects.create(
            name='测试仓库', code='WH001', location='测试'
        )
        self.store = Store.objects.create(
            name='测试门店', code='S001', address='测试', warehouse=self.warehouse
        )
        
        # 创建不同角色用户
        self.admin_user = User.objects.create_user('admin', password='pass123')
        Employee.objects.create(user=self.admin_user, role='admin')
        
        self.cashier_user = User.objects.create_user('cashier', password='pass123')
        Employee.objects.create(user=self.cashier_user, role='cashier', store=self.store)
    
    def test_admin_access_employee_list(self):
        """测试管理员可以访问员工列表"""
        self.client.login(username='admin', password='pass123')
        response = self.client.get(reverse('users:employee_list'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_cashier_cannot_access_employee_list(self):
        """测试收银员不能访问员工列表"""
        self.client.login(username='cashier', password='pass123')
        response = self.client.get(reverse('users:employee_list'))
        
        # 应该被重定向
        self.assertEqual(response.status_code, 302)