from django.db import models
from django.utils import timezone
from brandsandcategories.models import Category
from django.core.exceptions import ValidationError

TARGET_TYPE_CHOICES = (
    ('product', 'Product'),
    ('category', 'Category'),
)


class Offer(models.Model):
    name = models.CharField(max_length=200)
    offer_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    discount_percentage = models.PositiveSmallIntegerField(default=0)
    product = models.ManyToManyField(
        'products.Product', blank=True, related_name='product_offers')
    category = models.ManyToManyField(
        Category, blank=True, related_name='category_offers')

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

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
