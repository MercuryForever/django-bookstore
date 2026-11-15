from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceive, PurchaseReceiveItem
from inventory.models import Product, Warehouse


class SupplierForm(forms.ModelForm):
    """供应商表单"""
    
    class Meta:
        model = Supplier
        fields = ['name', 'code', 'contact', 'phone', 'email', 'address', 'bank_name', 'bank_account']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PurchaseOrderForm(forms.ModelForm):
    """采购订单表单"""
    
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'warehouse', 'expected_date', 'remark']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'expected_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    """采购订单明细表单"""
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
        }


# 创建内联表单集
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
)


class PurchaseReceiveForm(forms.ModelForm):
    """收货表单"""
    
    class Meta:
        model = PurchaseReceive
        fields = ['store', 'remark']
        widgets = {
            'store': forms.Select(attrs={'class': 'form-select'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }