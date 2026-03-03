from django.db import models
from brandsandcategories.models import Brand, Category
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from offer.utils import get_best_offer

# Create your models here.

# =========================
# PRODUCT 
# =========================
class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(max_length=250,blank=True,null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,blank=True,null=True, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL,blank=True,null=True, related_name="products")
    material = models.CharField(max_length=100,blank=True,null=True)
    is_active = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_selective = models.BooleanField(default=False)
    is_most_demanded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    auto_disabled = models.BooleanField(default=False)

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
        self.full_clean() 

        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug

        category_inactive = self.category and not self.category.is_active
        brand_inactive = self.brand and not self.brand.is_active

        if category_inactive or brand_inactive:
            self.is_active = False
            self.auto_disabled = True
        elif self.is_active:
            self.auto_disabled = False
        super().save(*args, **kwargs)

    def update_status_from_variants(self):
        has_active_variant = self.variants.filter(is_active=True).exists()
        category_inactive = self.category and not self.category.is_active
        brand_inactive = self.brand and not self.brand.is_active

        new_status = has_active_variant and not (category_inactive or brand_inactive)

        if self.is_active != new_status:
            self.is_active = new_status
            self.auto_disabled = not new_status
            super(Product, self).save(update_fields=["is_active", "auto_disabled"])

    def clean(self):
        if self.is_active:
            has_active_variant = self.variants.filter(is_active=True).exists()
            if not has_active_variant:
                raise ValidationError({
                    "is_active": "Cannot activate product without active variants."
                })
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

    size = models.ForeignKey(Size, on_delete=models.PROTECT,null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.PROTECT,null=True, blank=True)

    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    sales_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size', 'color'],
                name='unique_variant_combination'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"
    
    
    # ---------- Derived values ----------

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first()
    
    @property
    def is_available(self):
        return self.is_active and self.product.is_active

    # ---------- Validation ----------
    def clean(self):
        errors = {}

        if self.base_price is None or self.base_price <= 0:
            errors['base_price'] = "Base price must be greater than zero."

        if (
            self.sales_price is not None and
            self.base_price is not None and
            self.sales_price >= self.base_price
        ):
            errors['sales_price'] = "Sales price must be less than base price."

        if errors:
            raise ValidationError(errors)
    
    def get_pricing_data(self, offer=None):
        if offer is None:
            from offer.utils import get_best_offer
            offer = get_best_offer(self.product)

        prices = [self.base_price]
        discounts = [0]

        # Sales Price Logic
        if self.sales_price and self.sales_price < self.base_price:
            prices.append(self.sales_price)
            sales_discount = int(((self.base_price - self.sales_price) / self.base_price) * 100)
            discounts.append(sales_discount)

        # Offer Logic
        if offer and self.base_price > 0:
            discount_amount = (self.base_price * offer.discount_percentage) / 100
            offer_price = max(0, round(self.base_price - discount_amount))
            prices.append(offer_price)
            discounts.append(offer.discount_percentage)

        return {
            'final_price': min(prices),
            'discount_percentage': max(discounts),
            'active_offer': offer
        }
    
    @property
    def final_price(self):
        return self.get_pricing_data()['final_price']

    @property
    def discount_percentage(self):
        return self.get_pricing_data()['discount_percentage']

    @property
    def stock_status(self):
        if self.stock <= 0:
            return "Out of Stock"
        elif self.stock <= 10: 
            return "Low Stock"
        return "In Stock"
    
    @property
    def stock_badge_class(self):
        if self.stock <= 0:
            return "bg-danger"   
        elif self.stock <= 10:
            return "bg-warning text-dark"
        return "bg-success"      
    
    def save(self, *args, **kwargs):
        self.full_clean()   
        super().save(*args, **kwargs)
        self.product.update_status_from_variants()
        
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


 


        
   
