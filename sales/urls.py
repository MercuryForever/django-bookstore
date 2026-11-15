from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # 会员管理
    path('members/', views.member_list, name='member_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/update/', views.member_update, name='member_update'),
    
    # 收银台
    path('pos/', views.pos, name='pos'),
    path('pos/checkout/', views.pos_checkout, name='pos_checkout'),
    
    # 销售记录
    path('', views.sale_list, name='sale_list'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('export/', views.export_sales, name='export_sales'),
    
    # 统计
    path('ranking/', views.sales_ranking, name='sales_ranking'),
    
    # API
    path('api/members/search/', views.api_member_search, name='api_member_search'),
    path('api/check-discount/', views.api_check_discount, name='api_check_discount'),
    path('api/sales/trend/', views.sales_trend, name='sales_trend'),
]