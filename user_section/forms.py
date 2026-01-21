from django import forms
from accounts.models import CustomUser
from .models import UserAddress
from django.core.exceptions import ValidationError


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'gender']
        widgets = {
            'first_name':forms.TextInput(attrs={'class':'form-control'}),
            'last_name':forms.TextInput(attrs={'class':'form-control'}),
            'email':forms.EmailInput(attrs={'class':'form-control'}),
            'phone':forms.TextInput(attrs={'class':'form-control'}),
            'gender':forms.Select(attrs={'class':'form-control'})
        }
    def clean_first_name(self):
        name = self.cleaned_data.get("first_name")
        if not name.isalpha():
            raise ValidationError("First name must contain only letters.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get("last_name")
        if not name.isalpha():
            raise ValidationError("Last name must contain only letters.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be 10 digits.")
        return phone

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        
        fields = [
            'address_line_1', 'address_line_2', 'city', 
            'state', 'pincode', 'country', 'address_type', 'is_default'
        ]
        
        widgets = {
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(),
            'city': forms.TextInput(attrs={'placeholder': 'Enter city'}),
            'state': forms.TextInput(attrs={'placeholder': 'Enter state'}),
            'pincode': forms.TextInput(attrs={'placeholder': 'Enter pincode'}),
            'country': forms.TextInput(attrs={'placeholder': 'Enter country'}),
            'address_type': forms.RadioSelect(),
        }
        