from django import forms
from accounts.models import CustomUser
from .models import UserAddress
from django.core.exceptions import ValidationError
import re


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
    
    def clean_address_line_1(self):
        address = self.cleaned_data.get('address_line_1', '').strip()
        if not address:
            raise ValidationError("Address Line 1 cannot be empty.")
        if len(address) < 5:
            raise ValidationError("Address must be at least 5 characters long.")
        if not re.match(r'^[A-Za-z\s,.-]+$', address):
            raise ValidationError(
                "Address can contain only letters, spaces, comma, dot or hyphen."
            )

        return address


    def clean_address_line_2(self):
        address = self.cleaned_data.get('address_line_2')
        if address:  
            if len(address) < 3:
                raise ValidationError("Address Line 2 must be at least 3 characters.")
            if not re.match(r'^[A-Za-z\s,.-]+$', address):
                raise ValidationError(
                    "Address can contain only letters, numbers, spaces, comma, dot or hyphen."
                )

        return address

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise ValidationError("City cannot be empty.")
        if not all(x.isalpha() or x.isspace() for x in city):
            raise ValidationError("City should only contain letters and spaces.")
        return city

    def clean_state(self):
        state = self.cleaned_data.get('state', '').strip()
        if not state:
            raise ValidationError("State cannot be empty.")
        if not all(x.isalpha() or x.isspace() for x in state):
            raise ValidationError("State should only contain letters and spaces.")
        return state

    def clean_country(self):
        country = self.cleaned_data.get('country', '').strip()
        if not country:
            raise ValidationError("Country cannot be empty.")
        if not all(x.isalpha() or x.isspace() for x in country):
            raise ValidationError("Country should only contain letters and spaces.")
        return country

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '').strip()
        if pincode:
            if not pincode.isdigit():
                raise ValidationError("Pincode must contain only digits.")
            if len(pincode) != 6:
                raise ValidationError("Pincode must be exactly 6 digits.")
        return pincode
        