from django.db import models
from django.conf import settings
from user_section.models import UserAddress
from products.models import ProductVariant
import uuid
from django.utils import timezone
from django.db.models import Count, Q


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
        ('partially_refunded','Partially Refunded'),
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

    coupon = models.ForeignKey('offer.Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    # autogenerate the order id
    def save(self,*args, **kwargs):
        if not self.orderid:
            self.orderid= f"ORD-{uuid.uuid4().hex[:10].upper()}"
        # Ensure payment_status has a value
        if not self.payment_status:
            self.payment_status = 'pending'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id}"
    
    

    def update_order_status(self):
        # One query to rule them all
        stats = self.items.aggregate(
            total=Count('id'),
            cancelled=Count('id', filter=Q(status='cancelled')),
            returned=Count('id', filter=Q(return_status='returned')),
            requested=Count('id', filter=Q(return_status='return_requested')),
            approved=Count('id', filter=Q(return_status='return_approved')),
            rejected=Count('id', filter=Q(return_status='return_rejected')),
            delivered_none=Count('id', filter=Q(status='delivered', return_status='none'))
        )

        total = stats['total']
        if total == 0: return

        # Use the aggregated data
        if stats['cancelled'] == total:
            new_status = 'cancelled'
        elif stats['returned'] == total:
            new_status = 'returned'
        elif stats['approved'] > 0 and (stats['approved'] + stats['returned'] + stats['cancelled']) == total:
            new_status = 'return_approved'
        elif stats['returned'] > 0:
            new_status = 'partially_returned'
        elif stats['requested'] > 0:
            new_status = 'return_requested'
        elif (stats['delivered_none'] + stats['rejected'] + stats['cancelled']) == total:
            new_status = 'delivered'
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
        ('failed', 'Failed'),
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