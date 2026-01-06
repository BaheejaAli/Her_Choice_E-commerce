from django.db import models
from django.core.validators import FileExtensionValidator
from PIL import Image

# Create your models here.


# ================== BRAND MODEL ==================

class Brand(models.Model):
    name = models.CharField(
        max_length=100, unique=True, blank=False, help_text="Brand name (must be unique)"
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
    image = models.ImageField(upload_to="categories/images/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],)
    # Soft delete / status toggle
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
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            img = Image.open(self.image.path)
            target_size = (400, 400)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(target_size)

            img.save(self.image.path, quality=85, optimize=True)
    


