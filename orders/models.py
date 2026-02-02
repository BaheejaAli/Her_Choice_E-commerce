from django.db import models
from django.conf import settings
from user_section.models import UserAddress
from products.models import ProductVariant
import uuid
from django.utils import timezone


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('return_rejected', 'Return Rejected'),
        ('partially_returned', 'Partially Returned'), 
        ('partially_cancelled', 'Partially cancelled'), 
        ("returned", "Returned"),
        ("failed", "Failed"),
    )

    ADMIN_STATUS_FLOW = {
        "pending": ["processing", "cancelled", "failed"],
        "processing": ["shipped", "cancelled"],
        "partially_cancelled": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": [],
        "return_requested": ["return_approved", "return_rejected"],
        "return_approved": ["returned"],
        "return_rejected": ["delivered"],
        "partially_returned": ["returned", "return_approved", "return_rejected"],
        "cancelled": [],
        "returned": [],
        "failed": [],
    }

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
    
    def update_order_status(self):
        items = self.items.all()
        total_items = items.count()
        if total_items == 0:
            return
        
        cancelled_count = items.filter(status='cancelled').count()
        returned_count = items.filter(return_status='returned').count()
        requested_count = items.filter(return_status='return_requested').count()
        approved_count = items.filter(return_status='return_approved').count()
        rejected_count = items.filter(return_status='return_rejected').count()  
        delivered_count = items.filter(status='delivered', return_status='none').count()

        if cancelled_count == total_items:
            new_status = 'cancelled'
        elif returned_count == total_items:
            new_status = 'returned'
        elif requested_count == total_items:
            new_status = 'return_requested'
        elif approved_count == total_items:
            new_status = 'return_approved'
        elif (delivered_count + rejected_count + cancelled_count) == total_items and returned_count == 0:
            new_status = 'delivered'
            
        elif requested_count > 0:
            new_status = 'return_requested'
    
        elif approved_count > 0 or returned_count > 0:
            new_status = 'partially_returned'
        elif cancelled_count > 0:
            new_status = 'partially_cancelled'
        else:
            new_status = self.status

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status', 'updated_at'])
    
    @property
    def has_cancellable_items(self):
        return self.items.exclude(status__in=['cancelled', 'delivered']).exists()
    



class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('ordered', 'Ordered'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    RETURN_STATUS = [
        ('none', 'No Return'),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('return_rejected', 'Return Rejected'),
        ('returned', 'Returned'),
        ('return_canceled','Return Cancelled'),
]
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    price = models.DecimalField( max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='ordered') 
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS, default='none') 
    return_reason = models.TextField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)
    # cancelled = models.BooleanField(default=False)
    # returned = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def total_price(self):
        return self.price * self.quantity   

    def __str__(self):
        return f"{self.order.id}-{self.variant}"
    
    def save(self, *args, **kwargs):
        if self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        if self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        if self.return_status == 'returned' and not self.returned_at:
            self.returned_at = timezone.now()
        super().save(*args, **kwargs)
        self.order.update_order_status()