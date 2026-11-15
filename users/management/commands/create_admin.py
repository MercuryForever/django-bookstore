from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Employee


class Command(BaseCommand):
    help = '创建初始管理员账号'
    
    def handle(self, *args, **options):
        # 检查是否已存在管理员
        if Employee.objects.filter(role='admin').exists():
            self.stdout.write(self.style.WARNING('管理员账号已存在'))
            return
        
        # 创建用户
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': '系统管理员',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            user.set_password('admin123')
            user.save()
        
        # 创建员工
        Employee.objects.get_or_create(
            user=user,
            defaults={
                'role': 'admin',
                'phone': '13800138000',
            }
        )
        
        self.stdout.write(self.style.SUCCESS('管理员创建成功！'))
        self.stdout.write(f'用户名: admin')
        self.stdout.write(f'密码: admin123')
