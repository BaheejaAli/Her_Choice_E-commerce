from django.db import models
from django.utils import timezone
from products.models import Product
from brandsandcategories.models import Category
from django.core.exceptions import ValidationError

TARGET_TYPE_CHOICES = (
    ('product','Product'),
    ('category','Category'),
)
DISCOUNT_TYPE_CHOICES = (
    ('percentage','Percentage'),
    ('fixed','Fixed Amount')
)

class Offer(models.Model):
    name = models.CharField( max_length=200)
    offer_type = models.CharField( max_length=20, choices=TARGET_TYPE_CHOICES)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField( max_digits=10, decimal_places=2)

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='product_offers')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='category_offers')


    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank= True)
    is_active = models.BooleanField(default= True)
    created_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        now = timezone.now()
        return (self.is_active and self.start_at <= now and (self.end_at is None or self.end_at >= now))
    
    def clean(self):
        super().clean() 
        
        if self.offer_type == 'product' and not self.product:
            raise ValidationError("You selected 'Product' type but didn't select a product.")
        if self.offer_type == 'category' and not self.category:
            raise ValidationError("You selected 'Category' type but didn't select a category.")

        if self.product and self.category:
            raise ValidationError("An offer cannot target both a Product and a Category at once.")
            
        if self.end_at and self.start_at > self.end_at:
            raise ValidationError("The end date cannot be earlier than the start date.")

    def is_valid(self):
        now = timezone.now()
        return (self.is_active and self.start_at <= now and (self.end_at is None or self.end_at >= now))
    
    def __str__(self):
        if self.product:
            target = self.product.name
        elif self.category:
            target = self.category.name
        else:
            target = "No Target"
            
        return f"{self.name} - {target}"