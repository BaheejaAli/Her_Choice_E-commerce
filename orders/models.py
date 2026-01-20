from django.db import models
from django.conf import settings
from user_section.models import UserAddress


class Order(models.Model):
    STATUS_CHOICES = (
        ("placed", "Placed"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("return_requested", "Return Requested"),
        ("returned", "Returned"),
    )

    PAYMENT_METHODS = (
    ('cod', 'Cash on Delivery'),
    ('razorpay', 'Razorpay'),
    ('wallet', 'Wallet'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(UserAddress, on_delete=models.CASCADE)
    orderid = models.CharField(max_length=20, unique=True, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="placed")
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)