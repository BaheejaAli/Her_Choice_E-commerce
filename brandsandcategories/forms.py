from django import forms
from .models import Brand, Category

# ================== BRAND MODELFORM ==================
class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "logo", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input-field",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-input-field",
                }
            ),
            "is_active": forms.Select(
                choices=[(True, "Active"), (False, "Inactive")],
                attrs={"class": "form-input-field"},
            ),
        }

        labels = {
            "is_active": "Status",
        }

        help_texts = {
            "name": "Brand name must be unique.",
            "logo": "Upload JPG, PNG, SVG, or WEBP image.",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        qs = Brand.objects.filter(name__iexact=name)

        if not name:
            raise forms.ValidationError("Brand name is required.")

        # Exclude self when updating
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A brand with this name already exists.")

        return name

    def clean_logo(self):
        image = self.cleaned_data.get("logo")
        if not image:
            raise forms.ValidationError("Brand logo is required.")
            
        if image and not isinstance(image, str):
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file too large. Max size is 2MB.")
        return image

# ================== CATEGORY MODELFORM ==================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Category Name (e.g., Dresses, Accessories)",
                    "class": "form-input-field",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter a short description...",
                    "class": "form-input-field",
                    "rows": 3,
                }
            ),
            "is_active": forms.Select(
                choices=[(True, "Active"), (False, "Inactive")],
                attrs={"class": "form-input-field"},
            ),
        }
        labels = {
            "is_active": "Status",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Category name is required.")
        query = Category.objects.filter(name__iexact=name)

        # If editing an existing category, don't count itself as a duplicate
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise forms.ValidationError(
                f"A category with the name '{name}' already exists."
            )

        return name

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        if len(description) > 250:
            raise forms.ValidationError(
                "Description must be shorter than 250 characters."
            )

        return description

    