from django.db import models
from brandsandcategories.models import Brand,Category

# Create your models here.

# ================== PRODUCT MODEL ==================
class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    image = models.ImageField(upload_to="products/images", blank=True, null=True)
    alt_text = models.CharField(max_length=250, blank=True, null=True)
    description = models.TextField(
        max_length=250,
        help_text="Brief description of the category",
        blank=True,
        null=True,
    )
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    offer_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name= "products")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_selective = models.BooleanField(default=False)
    is_most_demanded = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category","is_active"]),
            models.Index(fields= ["is_featured"]),
            models.Index(fields= ["is_most_demanded"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["slug"])
            ]


    def __str__(self):
        return self.name