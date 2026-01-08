from django import forms
from accounts.models import CustomUser
from .models import UserAddress

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
        