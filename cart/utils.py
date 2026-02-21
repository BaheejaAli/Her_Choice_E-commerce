from django.db import transaction
from django.db.models import F
from orders.models import Order, OrderItem
from offer.models import Coupon, CouponUsage

def create_order_instance(request, address, subtotal, total_discount, coupon_discount, tax, total, delivery_charge, payment_method, payment_status="pending"):
    """Creates a new Order record in the database."""
    return Order.objects.create(
        user=request.user,
        address=address,
        billing_address=address,
        payment_method=payment_method,
        payment_status=payment_status,
        subtotal=subtotal,
        discount=total_discount + coupon_discount,
        tax=tax,
        total=total,
        status="pending",
        delivery_charge=delivery_charge
    )


def create_order_items(order, cart_items):
    """Creates OrderItem records for the order (no stock deduction)."""
    if order.items.exists():
        return
        
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.get_pricing_data()["final_price"]
        )


@transaction.atomic
def finalize_order(order, cart_items, cart, applied_coupon):
    """Handles stock reduction and cart deactivation after payment confirmation."""
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.get_pricing_data()["final_price"]
        )
        
        # Use database-level filter to ensure stock doesn't go negative
        from products.models import ProductVariant
        updated = ProductVariant.objects.filter(
            id=item.variant.id, 
            stock__gte=item.quantity
        ).update(stock=F("stock") - item.quantity)
        
        if not updated:
            raise ValueError(f"Not enough stock for {item.variant.product.name}")
    
    if applied_coupon:
        # Enforce global coupon limit
        updated = Coupon.objects.filter(
            id=applied_coupon.id, 
            used_count__lt=F('limit')
        ).update(used_count=F("used_count") + 1)
        
        if not updated:
            raise ValueError("Coupon usage limit reached")

        # Enforce per-user limit
        usage, created = CouponUsage.objects.get_or_create(
            user=order.user, 
            coupon=applied_coupon
        )
        updated_usage = CouponUsage.objects.filter(
            id=usage.id, 
            used_count__lt=applied_coupon.max_usage_per_user
        ).update(used_count=F("used_count") + 1)

        if not updated_usage:
            raise ValueError("You have already reached the usage limit for this coupon")
    
    cart.is_active = False
    cart.save(update_fields=["is_active"])


@transaction.atomic
def complete_order_payment(order, applied_coupon, cart):
    """Deducts stock, applies coupon, and deactivates cart after successful payment."""
    for item in order.items.select_related('variant'):
        # Use database-level filter to ensure stock doesn't go negative
        from products.models import ProductVariant
        updated = ProductVariant.objects.filter(
            id=item.variant.id, 
            stock__gte=item.quantity
        ).update(stock=F("stock") - item.quantity)
        
        if not updated:
            raise ValueError(f"Not enough stock for {item.variant.product.name}")
    
    if applied_coupon:
        # Enforce global coupon limit
        updated = Coupon.objects.filter(
            id=applied_coupon.id, 
            used_count__lt=F('limit')
        ).update(used_count=F("used_count") + 1)
        
        if not updated:
            raise ValueError("Coupon usage limit reached")

        # Enforce per-user limit
        usage, created = CouponUsage.objects.get_or_create(
            user=order.user, 
            coupon=applied_coupon
        )
        updated_usage = CouponUsage.objects.filter(
            id=usage.id, 
            used_count__lt=applied_coupon.max_usage_per_user
        ).update(used_count=F("used_count") + 1)

        if not updated_usage:
            raise ValueError("You have already reached the usage limit for this coupon")
    
    cart.is_active = False
    cart.save(update_fields=["is_active"])
