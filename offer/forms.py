from django import forms
from .models import Offer
from products.models import Product
from brandsandcategories.models import Category

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
        start_at = cleaned_data.get('start_at')
        end_at = cleaned_data.get('end_at')

        if offer_type == 'product':
            if not product or not product.exists():
                self.add_error('product', "Please select at least one product.")
            cleaned_data['category'] = Category.objects.none()

        if offer_type == 'category':
            if not category or not category.exists():
                self.add_error('category', "Please select at least one category.")
            cleaned_data['product'] = Product.objects.none()

        return cleaned_data
