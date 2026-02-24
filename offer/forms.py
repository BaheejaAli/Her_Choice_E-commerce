from django import forms
from .models import Offer
from products.models import Product
from brandsandcategories.models import Category
from .models import Coupon
from django.core.exceptions import ValidationError

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
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'product': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'category': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'start_at': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'end_at': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        discount = cleaned_data.get('discount_percentage')
        offer_type = cleaned_data.get('offer_type')
        product = cleaned_data.get('product')
        category = cleaned_data.get('category')
        start_at = cleaned_data.get('start_at')
        end_at = cleaned_data.get('end_at')

        errors = {}
        if not name or not name.strip():
            errors['name'] = "Offer name cannot be empty."
        elif len(name.strip()) < 3:
            errors['name'] = "Offer name must be at least 3 characters long."

        if discount is not None and not (1 <= discount <= 100):
            errors['discount_percentage'] = "Discount percentage must be between 1 and 100."

        if offer_type == 'product':
            if not product or not product.exists():
                errors['product'] = "Please select at least one product."
            cleaned_data['category'] = Category.objects.none()

        if offer_type == 'category':
            if not category or not category.exists():
                errors['category'] = "Please select at least one category."
            cleaned_data['product'] = Product.objects.none()

        start_at = cleaned_data.get('start_at')
        end_at = cleaned_data.get('end_at')
        if not end_at:
            errors['end_at'] = "End date is required."
        if start_at and end_at and end_at < start_at:
            errors['end_at'] = "End date must be after start date."

        if errors:
            raise ValidationError(errors)
        
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
            }),
            'max_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500',
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1000',
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
            }),
            'max_usage_per_user': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })

        }

    def clean(self):
        cleaned_data = super().clean()

        code = cleaned_data.get('code')
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount = cleaned_data.get('discount_percentage')

        errors = {}

        if not code or not code.strip():
            errors['code'] = "Coupon code cannot be empty."
        else:
            cleaned_data['code'] = code.strip().upper()

        if valid_from and valid_to and valid_to < valid_from:
            errors['valid_to'] = "End date must be after start date."

        if discount is not None and not (1 <= discount <= 100):
            errors['discount_percentage'] = "Discount must be between 1 and 100."

        if errors:
            raise ValidationError(errors)

        return cleaned_data
    



