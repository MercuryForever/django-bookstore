from django import forms
from .models import Member


class MemberForm(forms.ModelForm):
    """会员表单"""
    
    class Meta:
        model = Member
        fields = ['name', 'gender', 'birth_date', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.RadioSelect,
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MemberSearchForm(forms.Form):
    """会员搜索表单"""
    
    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '会员卡号/姓名/手机号'
        })
    )