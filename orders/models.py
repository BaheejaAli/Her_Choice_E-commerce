from django.db import models
from django.conf import settings
from user_section.models import UserAddress
from products.models import ProductVariant
import uuid


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
        ("failed", "Failed"),
    )

    PAYMENT_METHODS = (
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
        ('wallet', 'Wallet'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(UserAddress, on_delete=models.CASCADE)
    billing_address = models.ForeignKey(UserAddress, on_delete=models.CASCADE, related_name="billing_orders", null=True, blank=True)
    orderid = models.CharField(max_length=20, unique=True, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # autogenerate the order id
    def save(self,*args, **kwargs):
        if not self.orderid:
            self.orderid= f"ORD-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ("shipped", "Shipped"),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    RETURN_STATUS = [
        ('none', 'Not Requested'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    price = models.DecimalField( max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending') 
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS, default='none') 
    cancelled = models.BooleanField(default=False)
    returned = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def total_price(self):
        return self.price * self.quantity   

    def __str__(self):
        return f"{self.order.id}-{self.variant}"