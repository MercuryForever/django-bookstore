from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # 库存查询
    path('', views.inventory_list, name='list'),
    path('<int:pk>/', views.inventory_detail, name='detail'),
    path('low-stock/', views.low_stock_list, name='low_stock'),
    
    # 库存调拨
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/approve/', views.transfer_approve, name='transfer_approve'),
    path('transfers/<int:pk>/execute/', views.transfer_execute, name='transfer_execute'),
    path('transfers/<int:pk>/cancel/', views.transfer_cancel, name='transfer_cancel'),
    
    # 库存盘点
    path('checks/', views.check_list, name='check_list'),
    path('checks/create/', views.check_create, name='check_create'),
    path('checks/<int:pk>/', views.check_detail, name='check_detail'),
    path('checks/<int:pk>/update/', views.check_update, name='check_update'),
    path('checks/<int:pk>/complete/', views.check_complete, name='check_complete'),
    
    # API
    path('api/stock/<int:store_id>/<int:product_id>/', views.api_product_stock, name='api_stock'),
    path('api/products/search/', views.api_product_search, name='api_product_search'),
]