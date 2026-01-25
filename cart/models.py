from django.db import models
from django.conf import settings
from products.models import ProductVariant
from django.db.models import Q


# Create your models here.
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_active=True),
                name="unique_active_cart_per_user"
            )
        ]
    
    @property
    def get_total_price(self):
        return sum(item.sub_total for item in self.items.all())
    
    @property
    def get_total_base_price(self):
        return sum(item.base_sub_total for item in self.items.all())
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    def __str__(self):
        return f"Cart - {self.user}, active={self.is_active}"
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart","variant")

    @property
    def sub_total(self):
        return self.quantity * self.variant.final_price
    
    @property
    def base_sub_total(self):
        return self.quantity * self.variant.base_price
    


    

