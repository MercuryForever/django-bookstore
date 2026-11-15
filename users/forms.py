from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Employee


class LoginForm(AuthenticationForm):
    """登录表单"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '用户名'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '密码'
        })
    )


class EmployeeForm(forms.ModelForm):
    """员工表单"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='用户名'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='密码',
        required=False,
        help_text='留空则不修改密码'
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='姓名'
    )
    
    class Meta:
        model = Employee
        fields = ['role', 'store', 'phone']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'store': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance and instance.user:
            initial = kwargs.get('initial', {})
            initial['username'] = instance.user.username
            initial['first_name'] = instance.user.first_name
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        
        if employee.pk:
            # 更新现有用户
            user = employee.user
            user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            if self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])
            user.save()
        else:
            # 创建新用户
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                password=self.cleaned_data['password'] or 'password123',
                first_name=self.cleaned_data['first_name']
            )
            employee.user = user
        
        if commit:
            employee.save()
        return employee
