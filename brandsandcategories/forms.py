from django import forms
from .models import Brand, Category


class BrandForm(forms.ModelForm):
    """Base form for creating/editing a Brand object (used by Admin)."""

    class Meta:
        model = Brand
        fields = ["name", "logo", "description", "is_active"]
        # Add necessary widgets and classes for styling
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Brand Name (e.g., Her Choice)",
                    "class": "form-input-field",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Brief description of the brand",
                    "class": "form-input-field",
                }
            ),
            "is_active": forms.Select(
                choices=[(True, "Active"), (False, "Inactive")],
                attrs={"class": "form-input-field"},
            ),
        }
        # labels = {
        #     'is_active': 'Status (Visibility)',
        # }


# class CategoryForm(forms.ModelForm):
#     class Meta:
#         model = Category
#         fields = ["name", "image", "is_active"]
#         widgets = {
#             "name": forms.TextInput(
#                 attrs={
#                     "placeholder": "Category Name (e.g., Dresses, Accessories)",
#                     "class": "form-input-field",
#                 }
#             ),
#             'is_active': forms.Select(
#                 choices=[(True, 'Active'), (False, 'Inactive')],
#                 attrs={'class': 'form-input-field'}
#             ),
#         }
#         labels = {
#             'is_active': 'Status (Visibility)',
#         }
