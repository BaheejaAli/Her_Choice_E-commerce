from django import forms
from .models import Offer
from products.models import Product
from brandsandcategories.models import Category
from .models import Coupon

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = [
            'name', 'offer_type', 'discount_percentage',
            'product', 'category', 'start_at', 'end_at', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Summer Sale'}),
            'offer_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'product': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'category': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'start_at': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'end_at': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        product = cleaned_data.get('product')
        category = cleaned_data.get('category')

        if offer_type == 'product':
            if not product or not product.exists():
                self.add_error('product', "Please select at least one product.")
            cleaned_data['category'] = Category.objects.none()

        if offer_type == 'category':
            if not category or not category.exists():
                self.add_error('category', "Please select at least one category.")
            cleaned_data['product'] = Product.objects.none()

        return cleaned_data
    
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code',
            'discount_percentage',
            'max_discount_amount',
            'minimum_amount',
            'valid_from',
            'valid_to',
            'limit',
            'max_usage_per_user',
            'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SAVE10',
                'style': 'text-transform: uppercase;'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '1'
            }),
            'max_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500',
                'step': '0.01',
                'min': '0'
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1000',
                'step': '0.01',
                'min': '0',
                'value': '0'
            }),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'valid_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'max_usage_per_user': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1',
                'min': '1',
                'value': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })

        }
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
        return code
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount_percentage = cleaned_data.get('discount_percentage')

        if valid_from and valid_to and valid_to <= valid_from:
            raise forms.ValidationError(
                'Valid To date must be after Valid From date.'
            )

        if discount_percentage is not None:  
            if discount_percentage > 100 :
                raise forms.ValidationError(
                    'Percentage discount cannot exceed 100%.'
                )
            if discount_percentage <= 0:
                raise forms.ValidationError(
                    'Discount value must be greater than 0.'
                )
            
        return cleaned_data
    



