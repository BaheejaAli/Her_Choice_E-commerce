from django.db import models,transaction
from products.models import ProductVariant
from django.conf import settings

# Create your models here.

class UserAddress(models.Model):
    ADDRESS_TYPES = (
        ('home','Home'),
        ('work','Work'),
        ('other','Other'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    address_line_1 = models.CharField( max_length=255)
    address_line_2 = models.CharField( max_length=255, blank=True, null=True)
    city = models.CharField( max_length=100)
    state = models.CharField( max_length=100)
    pincode = models.CharField( max_length=10)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_type} - {self.user.email}"
    
    # Ensure only one default address per user
    def save(self, *args, **kwargs):
        if self.is_default:
            with transaction.atomic():
                UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
                super().save(*args, **kwargs)
        else:
            if not UserAddress.objects.filter(user=self.user).exists():
                self.is_default = True
            super().save(*args, **kwargs)

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Wishlist of {self.user.get_full_name}'
    
class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="wishlist_items")
    added_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField( auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['wishlist','variant'],
                                    name = 'unique_wishlist_variant')
        ]

class Contact(models.Model):
    INQUIRY_TYPES = (
        ('order', 'Order Inquiry'),
        ('product', 'Product Question'),
        ('shipping', 'Shipping & Returns'),
        ('technical', 'Technical Support'),
        ('other', 'Other'),
    )
    name = models.CharField( max_length=150)
    email = models.EmailField()
    inquiry_type = models.CharField( max_length=20, choices=INQUIRY_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.inquiry_type}"

