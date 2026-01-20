from django.db import models
from brandsandcategories.models import Brand, Category
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from io import BytesIO
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_delete
from django.dispatch import receiver
import cloudinary.uploader

# Create your models here.

# =========================
# PRODUCT 
# =========================
class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(max_length=250,blank=True,null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    material = models.CharField(max_length=100,blank=True,null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_selective = models.BooleanField(default=False)
    is_most_demanded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["is_most_demanded"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["slug"])
        ]

    def __str__(self):
        return self.name

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
        if not self.category.is_active or not self.brand.is_active:
            self.is_active = False
        super().save(*args, **kwargs)

# =========================
# SIZE
# =========================
class Size(models.Model):
    name = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name


# =========================
# COLOR
# =========================
class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7,blank=True,
        null=True,)
    def __str__(self):
        return self.name
    
# =========================
# PRODUCT VARIANT 
# =========================
class ProductVariant(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="variants")

    size = models.ForeignKey(Size, on_delete=models.CASCADE,null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)

    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    offer_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'size', 'color')
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"

    # ---------- Derived values ----------

    @property
    def final_price(self):
        return self.offer_price if self.offer_price else self.base_price

    @property
    def discount_percentage(self):
        if self.offer_price and self.base_price > self.offer_price:
            discount = ((self.base_price - self.offer_price) /
                        self.base_price) * 100
            return int(discount)
        return 0
    
    @property
    def discount_value(self):
        if self.offer_price and self.base_price > self.offer_price:
            return self.base_price - self.offer_price
        return 0
    
    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first()

    # ---------- Validation ----------
    def clean(self):
        errors = {}

        if self.base_price <= 0:
            errors['base_price'] = "Base price must be greater than zero."

        if self.offer_price and self.offer_price >= self.base_price:
            errors['offer_price'] = "Offer price must be less than base price."

        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()   
        super().save(*args, **kwargs)
        
# =========================
# PRODUCT VARIANT IMAGE
# =========================
class ProductVariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to="variant-images/",validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    alt_text = models.CharField(max_length=250, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.variant} Image"
    
    def save(self, *args, **kwargs):

        # PRIMARY IMAGE LOGIC (unchanged)
        if not ProductVariantImage.objects.filter(variant=self.variant).exists():
            self.is_primary = True

        if self.is_primary:
            ProductVariantImage.objects.filter(
                variant=self.variant,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

@receiver(post_delete, sender=ProductVariantImage)
def delete_image_from_cloudinary(sender, instance, **kwargs):
    """
    Automatically deletes the image file from Cloudinary 
    when the ProductVariantImage record is deleted.
    """
    if instance.image:
        try:
            cloudinary.uploader.destroy(instance.image.public_id)
        except Exception as e:
            print(f"Cloudinary deletion failed: {e}")

 


        
   
