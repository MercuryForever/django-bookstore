from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    """员工模型，扩展Django User"""
    
    ROLE_CHOICES = [
        ('admin', '系统管理员'),
        ('manager', '店长'),
        ('cashier', '收银员'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='employee',
        verbose_name='用户账号'
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='cashier',
        verbose_name='角色'
    )
    store = models.ForeignKey(
        'inventory.Store', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='所属门店'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '员工'
        verbose_name_plural = '员工'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_cashier(self):
        return self.role == 'cashier'