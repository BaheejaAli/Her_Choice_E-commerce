from django.db import models
from brandsandcategories.models import Brand,Category
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from PIL import Image

# Create your models here.

# ================== PRODUCT MODEL ==================
class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True,blank=True)
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

    stock = models.PositiveIntegerField(default=0, help_text="Current inventory count")
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name= "products")
    
    # Status flags
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
    
    # Calculate Discount Percentage for Template
    @property
    def discount_percentage(self):
        if self.offer_price and self.base_price > self.offer_price:
            discount = ((self.base_price - self.offer_price) / self.base_price) * 100
            return int(discount)
        return 0
    
    # Auto slug generation
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # Price validation
    def clean(self):
        if self.base_price <= 0:
            raise ValidationError("Base price must be greater than zero")
    
        if self.offer_price and self.offer_price >= self.base_price:
            raise ValidationError("Offer price must be less than base price")


# ================== PRODUCT IMAGE MODEL ==================
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/images/")
    alt_text = models.CharField(max_length=250, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} Image"
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs) 

    #     if self.image:
    #         img = Image.open(self.image.path)

        
    #         if img.height > 800 or img.width > 800:
    #             output_size = (800, 800)
    #             img.thumbnail(output_size) 
    #             img.save(self.image.path)