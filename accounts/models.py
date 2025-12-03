from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# AbstractBaseUser provides core user authentication fields (password, last_login, is_active)
# BaseUserManager provides methods for creating users and superusers
# PermissionsMixin provides group/permission fields and methods (is_superuser, get_all_permissions)

# Create your models here.

class UserManager(BaseUserManager):
    """
    Custom user manager for the CustomUser model.
    Handles the creation of standard users and superusers.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a regular user with the given email and password.
        """
        if not email:
            raise ValueError("User must have an email")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        Sets necessary flags for administrative access.
        """
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True) ## Superusers should be active immediately

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model extending Django's base user functionality.
    Uses email as the unique identifier for authentication.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_pic = models.URLField( max_length=200, blank=True,null=True)

    # Permission/Status Flags
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)    
    is_staff = models.BooleanField(default=False)  # Needed for Django admin

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager assignment and required settings
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
