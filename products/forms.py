from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "base_price",
            "offer_price",
            "category",
            "brand",
            "is_active",
            "is_featured",
            "is_selective",
            "is_most_demanded",
            # slug is auto generated in the model
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Product name",
                    "class": "form-input-field",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Brief description of the product",
                    "class": "form-input-field",
                }
            ),
            "base_price": forms.NumberInput(
                attrs={
                    "placeholder": "Base price",
                    "class": "form-input-field",
                }
            ),
            "offer_price": forms.NumberInput(
                attrs={
                    "placeholder": "Offer price (optional)",
                    "class": "form-input-field",
                }
            ),
            "category": forms.Select(attrs={"class": "form-input-field"}),
            "brand": forms.Select(attrs={"class": "form-input-field"}),
            "is_active": forms.Select(
                choices=[(True, "Active"), (False, "Inactive")],
                attrs={"class": "form-input-field"},
            ),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_selective": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_most_demanded": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

        labels = {
            "is_active": "Status",
            "is_featured": "Featured",
            "is_selective": "Selective",
            "is_most_demanded": "Most Demanded",
        }

        help_texts = {
            "name": "Product name must be unique.",
            "base_price": "Enter the original product price.",
            "offer_price": "Offer price must be less than base price.",
        }

    # ---------- FIELD VALIDATIONS ----------
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError("Product name is required.")
        qs = Product.objects.filter(name__iexact=name)

        # Exclude current instance during edit
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A product with this name already exists.")

        return name

    def clean_base_price(self):
        base_price = self.cleaned_data.get("base_price")

        if base_price is None or base_price <= 0:

            raise forms.ValidationError("Base price must be greater than zero")
        return base_price

    def clean_offer_price(self):
        offer_price = self.cleaned_data.get("offer_price")
        base_price = self.cleaned_data.get("base_price")

        if offer_price is not None and base_price is not None:
            if offer_price >= base_price:
                raise forms.ValidationError("Offer price must be less than base price.")

        return offer_price


# Define the Image Formset
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=("image", "alt_text"),
    extra=1,  # This creates exactly 3 empty slots by default
    min_num=3,  # Ensures at least 3 forms are present
    validate_min=True,  # Tells Django to enforce the minimum of 3
    can_delete=True,  # Allows you to swap/remove images later
)
