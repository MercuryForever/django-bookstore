import os
import django
from decimal import Decimal

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse

# 创建测试客户端
client = Client()

# 测试登录
login_response = client.post('/users/login/', {
    'username': 'manager_S0001',
    'password': 'password123'
}, follow=True)

print(f'登录状态: {login_response.status_code}')
print(f'登录成功: {client.session.get("_auth_user_id") is not None}')

# 访问仪表盘
dashboard_response = client.get(reverse('dashboard'))
print(f'仪表盘状态: {dashboard_response.status_code}')

# 检查响应内容
content = dashboard_response.content.decode('utf-8')

# 检查商品销售排行是否有数据
if '商品销售排行' in content and '<tr>' in content:
    print('✓ 商品销售排行（本月）显示正常')
    # 计算行数
    rows = content.count('<tr>') - content.count('<tr class="table-active">') - content.count('<tr>')
    print(f'   显示行数: {rows}')
else:
    print('✗ 商品销售排行（本月）无数据')

# 检查最近销售记录是否有数据
if '最近销售记录' in content and '<tr>' in content:
    print('✓ 最近销售记录显示正常')
    # 计算行数
    rows = content.count('<tr>') - content.count('<tr class="table-active">') - content.count('<tr>')
    print(f'   显示行数: {rows}')
else:
    print('✗ 最近销售记录无数据')

# 检查是否有数据同步问题
if '暂无数据' not in content:
    print('✓ 仪表盘数据显示正常，无同步问题')
else:
    print('✗ 仪表盘部分数据显示为"暂无数据"')
