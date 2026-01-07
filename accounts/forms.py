from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import CustomUser

# ========= ADMIN AUTHENTICATION FORMS ==============


class AdminLoginForm(forms.Form):
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(
            attrs={"placeholder": "Enter your email", "class": "form-control"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your password", "class": "form-control"}
        )
    )
    remember = forms.BooleanField(required=False, label=" Remember Me")


class AdminForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(
            attrs={"placeholder": "Enter your admin email", "class": "form-control"}
        ),
    )


class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter new password", "class": "form-control"}
        ),
        label="New Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Confirm new password", "class": "form-control"}
        ),
        label="Confirm Password",
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
            try:
                # This checks for minimum length, common passwords, complexity, etc.
                validate_password(new_password)
            except ValidationError as e:
                # Add the detailed validation errors to the 'new_password' field
                self.add_error("new_password", e)

        return cleaned_data


# ========= USER AUTHENTICATION FORMS ==============


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="Password", widget=forms.PasswordInput(attrs={"placeholder": "Password", "class":"form-control"})
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password", "class":"form-control"}),
    )

    class Meta:
        model = CustomUser   
        fields = ("first_name","last_name", "email") 
        widgets = {
            "first_name" : forms.TextInput(attrs={"placeholder":"First Name", "class":"form-control"}),
            "last_name" : forms.TextInput(attrs={"placeholder":"Last Name", "class":"form-control"}),
            "email" : forms.EmailInput(attrs={"placeholder":"Email Address", "class":"form-control"}),
           
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error("password", e)
        return cleaned_data


class UserLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"placeholder": "Email address", "class": "form-control"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password", "class": "form-control"}
        )
    )


class UserForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(
            attrs={"placeholder": "Enter your account email", "class": "form-control"}
        ),
    )


class UserResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter new password", "class": "form-control"}
        ),
        label="New Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Confirm new password", "class": "form-control"}
        ),
        label="Confirm Password",
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
            try:
                validate_password(new_password)
            except ValidationError as e:
                self.add_error("new_password", e)

        return cleaned_data
    
    
