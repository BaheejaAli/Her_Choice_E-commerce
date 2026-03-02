from django.db import transaction
from django.db.models import F
from orders.models import Order, OrderItem
from offer.models import Coupon, CouponUsage

def check_any_out_of_stock(cart_items):
    """Checks if any item in the provided list is out of stock or unavailable."""
    return any(
        not item.variant.is_active or 
        not item.variant.product.is_active or 
        not item.variant.product.category.is_active or 
        not item.variant.product.brand.is_active or
        item.variant.stock <= 0 or 
        item.quantity > item.variant.stock 
        for item in cart_items
    )

def create_order_instance(request, address, subtotal, total_discount, coupon_discount, tax, total, delivery_charge, payment_method, applied_coupon=None, payment_status="pending"):
    """Creates a new Order record in the database."""
    return Order.objects.create(
        user=request.user,
        address=address,
        billing_address=address,
        payment_method=payment_method,
        payment_status=payment_status,
        subtotal=subtotal,
        discount=total_discount,
        coupon=applied_coupon,
        coupon_discount=coupon_discount,
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
            price=item.variant.final_price
        )


@transaction.atomic
def finalize_order(order, cart_items, cart, applied_coupon):
    """Handles stock reduction and cart deactivation after payment confirmation."""
    from products.models import ProductVariant
    
    for item in cart_items:
        # Lock the variant row to prevent race conditions
        variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
        
        if variant.stock < item.quantity:
            raise ValueError(f"Not enough stock for {variant.product.name}")
            
        variant.stock -= item.quantity
        variant.save()
        
        OrderItem.objects.create(
            order=order,
            variant=variant,
            quantity=item.quantity,
            price=variant.final_price
        )
    
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
    from products.models import ProductVariant
    
    for item in order.items.select_related('variant'):
        # Lock the variant row to prevent race conditions
        variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
        
        if variant.stock < item.quantity:
             raise ValueError(f"Not enough stock for {variant.product.name}")
             
        variant.stock -= item.quantity
        variant.save()
    
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
