from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.exceptions import ObjectDoesNotExist


def role_required(allowed_roles):
    """角色权限装饰器"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('users:login')
            
            try:
                employee = request.user.employee
                if employee.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, '您没有权限访问此页面')
                    return redirect('dashboard')
            except (AttributeError, ObjectDoesNotExist):
                messages.error(request, '请先完善员工信息')
                return redirect('dashboard')
        
        return wrapper
    return decorator


def admin_required(view_func):
    """管理员权限装饰器"""
    return role_required(['admin'])(view_func)


def manager_required(view_func):
    """店长及以上权限装饰器"""
    return role_required(['admin', 'manager'])(view_func)


def cashier_required(view_func):
    """收银员及以上权限装饰器"""
    return role_required(['admin', 'manager', 'cashier'])(view_func)