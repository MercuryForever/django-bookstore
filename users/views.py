from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Employee
from .forms import LoginForm, EmployeeForm
from .decorators import admin_required, manager_required


def login_view(request):
    """登录视图"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'欢迎回来，{user.get_full_name() or user.username}！')
            return redirect('dashboard')
        else:
            messages.error(request, '用户名或密码错误')
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """退出登录"""
    logout(request)
    messages.info(request, '您已退出登录')
    return redirect('users:login')


@login_required
@admin_required
def employee_list(request):
    """员工列表"""
    employees = Employee.objects.select_related('user', 'store').all()
    
    # 搜索
    search = request.GET.get('search', '')
    if search:
        employees = employees.filter(
            user__username__icontains=search
        ) | employees.filter(
            user__first_name__icontains=search
        ) | employees.filter(
            phone__icontains=search
        )
    
    # 角色筛选
    role = request.GET.get('role', '')
    if role:
        employees = employees.filter(role=role)
    
    # 分页
    paginator = Paginator(employees, 20)
    page = request.GET.get('page', 1)
    employees = paginator.get_page(page)
    
    return render(request, 'users/employee_list.html', {
        'employees': employees,
        'search': search,
        'role': role,
    })


@login_required
@admin_required
def employee_create(request):
    """创建员工"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '员工创建成功')
            return redirect('users:employee_list')
    else:
        form = EmployeeForm()
    
    return render(request, 'users/employee_form.html', {
        'form': form,
        'title': '新增员工'
    })


@login_required
@admin_required
def employee_edit(request, pk):
    """编辑员工"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, '员工信息已更新')
            return redirect('users:employee_list')
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'users/employee_form.html', {
        'form': form,
        'employee': employee,
        'title': '编辑员工'
    })


@login_required
@admin_required
def employee_delete(request, pk):
    """删除员工"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        user = employee.user
        employee.delete()
        user.delete()
        messages.success(request, '员工已删除')
        return redirect('users:employee_list')
    
    return render(request, 'users/employee_confirm_delete.html', {
        'employee': employee
    })
