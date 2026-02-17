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


def finalize_order(order, cart_items, cart, applied_coupon):
    """Handles stock reduction and cart deactivation after payment confirmation."""
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.get_pricing_data()["final_price"]
        )
        item.variant.stock -= item.quantity
        item.variant.save(update_fields=["stock"])
    
    if applied_coupon:
        Coupon.objects.filter(id=applied_coupon.id).update(used_count=F("used_count") + 1)
        usage, created = CouponUsage.objects.get_or_create(
            user=order.user, 
            coupon=applied_coupon
        )
        usage.used_count = F("used_count") + 1
        usage.save()
    
    cart.is_active = False
    cart.save(update_fields=["is_active"])
