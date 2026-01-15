from django.db import models
from django.core.validators import FileExtensionValidator
from PIL import Image

# Create your models here.


# ================== BRAND MODEL ==================
class Brand(models.Model):
    name = models.CharField(
        max_length=100, unique=True
    )

    logo = models.ImageField(
        upload_to="brands/logos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg", "webp"])],
    )

    description = models.TextField(
        max_length=500
    )

    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# ================== CATEGORY MODEL ==================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Category Name")
    description = models.TextField(
        max_length=250,
        help_text="Brief description of the category",
        blank=True,
        null=True,
    )
  
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["is_active"]),
    ]


    def __str__(self):
        return self.name

    

