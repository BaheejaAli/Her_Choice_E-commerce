from django.db import models
from django.core.validators import FileExtensionValidator
from PIL import Image

# Create your models here.


# ================== BRAND MODEL ==================
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(
        upload_to="brands/logos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg", "webp"])],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        was_inactive = False

        if self.pk:
            old = Brand.objects.get(pk=self.pk)
            was_inactive = not old.is_active and self.is_active

        super().save(*args, **kwargs)

        # If brand became active again
        if was_inactive:
            self.products.filter(auto_disabled=True).update(
                is_active=True,
                auto_disabled=False
            )


# ================== CATEGORY MODEL ==================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Category Name")
    is_active = models.BooleanField(default=True)
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
        was_inactive = False

        if self.pk:
            old = Category.objects.get(pk=self.pk)
            was_inactive = not old.is_active and self.is_active

        super().save(*args, **kwargs)

        # If category became active again
        if was_inactive:
            self.products.filter(auto_disabled=True).update(
                is_active=True,
                auto_disabled=False
            )

    

