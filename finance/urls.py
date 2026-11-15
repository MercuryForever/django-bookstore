from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('daily/', views.daily_report, name='daily_report'),
    path('monthly/', views.monthly_report, name='monthly_report'),
    path('daily/export/', views.export_daily_report, name='export_daily_report'),
    path('monthly/export/', views.export_monthly_report, name='export_monthly_report'),
    path('profit/', views.profit_analysis, name='profit_analysis'),
]