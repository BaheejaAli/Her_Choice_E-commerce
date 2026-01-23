from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductVariant, ProductVariantImage
from django.forms.widgets import ClearableFileInput

# =========================
# PRODUCT FORM
# =========================


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "material",
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
            "material": forms.TextInput(
                attrs={
                    "placeholder": "Material (e.g. Cotton, Rayon)",
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

    # ---------- FIELD VALIDATIONS ----------
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Product name is required.")

        qs = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A product with this name already exists.")

        return name


# =========================
# PRODUCT VARIANT FORM
# =========================
class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = [
            "size",
            "color",
            "base_price",
            "offer_price",
            "stock",
        ]
        widgets = {
            "size": forms.Select(attrs={"class": "form-input-field"}),
            "color": forms.Select(attrs={"class": "form-input-field"}),
            "base_price": forms.NumberInput(
                attrs={"class": "form-input-field", "min": 0}
            ),
            "offer_price": forms.NumberInput(
                attrs={"class": "form-input-field", "min": 0}
            ),
            "stock": forms.NumberInput(
                attrs={"class": "form-input-field", "min": 0}
            ),
        }

    # -------------------------------
    # FIELD LEVEL VALIDATIONS
    # -------------------------------
    def clean_color(self):
        color = self.cleaned_data.get("color")
        if not color:
            raise forms.ValidationError("Color is required.")
        return color


    def clean_base_price(self):
        base_price = self.cleaned_data.get("base_price")
        if base_price is None or base_price <= 0:
            raise forms.ValidationError(
                "Base price must be greater than zero."
            )
        return base_price

    def clean_offer_price(self):
        offer_price = self.cleaned_data.get("offer_price")
        base_price = self.cleaned_data.get("base_price")

        if offer_price is not None and base_price is not None:
            if offer_price >= base_price:
                raise forms.ValidationError(
                    "Offer price must be less than base price."
                )
        return offer_price

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        if stock is None or stock < 0:
            raise forms.ValidationError(
                "Stock cannot be negative."
            )
        return stock

    # -------------------------------
    # FORM LEVEL VALIDATION
    # -------------------------------
    def clean(self):
        cleaned_data = super().clean()
        size = cleaned_data.get("size")
        color = cleaned_data.get("color")

        # Product exists only during UPDATE
        product = self.instance.product if self.instance.pk else None

        if product and size and color:
            duplicate_qs = ProductVariant.objects.filter(
                product=product,
                size=size,
                color=color
            ).exclude(pk=self.instance.pk)

            if duplicate_qs.exists():
                self.add_error(
                    "color",
                    "Variant with this size and color already exists."
                )

        return cleaned_data


# =========================
# PRODUCT VARIANT IMAGE FORM
# =========================
class ProductVariantImageForm(forms.ModelForm):
    class Meta:
        model = ProductVariantImage
        fields = ("image",)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return image


# =========================
# PRODUCT IMAGE FORMSET
# =========================
ProductVariantImageFormSet = inlineformset_factory(
    ProductVariant,
    ProductVariantImage,
    form=ProductVariantImageForm,
    fields=("image",),
    # min_num=3,           
    # validate_min=True,
    extra=5,
    can_delete=True,
)
