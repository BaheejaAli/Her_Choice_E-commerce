

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_admin')
    list_filter = ('is_admin', 'is_staff', 'is_active')
    search_fields = ("email",)
    ordering = ("email",)

    # for editing existing users
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "profile_pic")}),
        ("Permissions", {"fields": ("is_active","is_staff", "is_admin", "is_superuser", "is_verified", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("last_login",)}),
    )

    # for adding a new user
    add_fieldsets = (
        (None, {
            "fields": ("email", "password1", "password2", "is_staff", "is_superuser")
        }),
    ) 

admin.site.register(CustomUser, CustomUserAdmin)

