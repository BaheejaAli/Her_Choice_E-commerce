from django.db import models
from django.core.validators import FileExtensionValidator

# Create your models here.


# ================== BRAND MODEL ==================
class Brand(models.Model):
    name = models.CharField(
        max_length=100, unique=True, help_text="Brand name (must be unique)"
    )

    logo = models.ImageField(
        upload_to="brands/logos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg", "webp"])],
        help_text="Brand logo image",
    )

    description = models.TextField(
        max_length=500, help_text="Brief description of the brand"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Status: True for Active (visible), False for Inactive/Soft Delete",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name


# ================== CATEGORY MODEL ==================
class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., Casual, Formal, Ethnic, Dresses)",
    )

    image = models.ImageField(
        upload_to="categories/images/",
        blank=True,
        null=True,
        help_text="Image representing the category on the admin dashboard",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Status: True for Active (visible), False for Inactive/Soft Delete"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
