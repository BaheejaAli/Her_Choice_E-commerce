from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from products.models import Product, ProductVariant
from .models import Cart, CartItem
from django.views.decorators.http import require_POST
from django.contrib import messages
from user_section.models import UserAddress, WishlistItem
from orders.models import Order, OrderItem
from offer.models import Coupon
from django.db import transaction
import razorpay
from django.conf import settings
from .utils import create_order_instance, create_order_items, finalize_order, complete_order_payment
from decimal import Decimal
from wallet.models import WalletTransaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

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

@require_POST
@login_required
def add_to_cart(request):
    try:
        variant_id = request.POST.get("variant_id")

        if not variant_id:
            return JsonResponse({
                "status": "error",
                "message": "Variant ID is required"
            }, status=400)

        variant = get_object_or_404(
            ProductVariant,
            id=variant_id,
            is_active=True,
            product__is_active=True,
            product__category__is_active=True,
            product__brand__is_active=True
        )
        if variant.stock <= 0:
            return JsonResponse({
                "status": "error",
                "message": "Out of stock"
            }, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        cartItem, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={"quantity": 1})

        if not created:
            max_allowed = min(variant.stock, 5)
            if cartItem.quantity >= max_allowed:
                if variant.stock < 5:
                    if variant.stock == 1:
                        message = "You already have the only available unit in your cart."
                    else:
                        message = f"You already have all {variant.stock} available units in your cart."
                else:
                    message = "Maximum 5 units allowed per item."
                return JsonResponse({
                    "status": "error",
                    "message": message,
                    "data": {
                        "available_stock": variant.stock
                    }
                }, status=400)

            cartItem.quantity += 1
            cartItem.save(update_fields=["quantity"])

        # Remove from wishlist
        WishlistItem.objects.filter(
            wishlist__user=request.user, variant=variant).delete()

        return JsonResponse({
            "status": "success",
            "message": "Item added to cart successfully",
            "data": {
                "cart_count": cart.total_items,
            }
        }, status=200)

    except Exception as e:
        print("ADD TO CART ERROR:", e)
        return JsonResponse({
            "status": "error",
            "message": "Server error"
        }, status=500)


def cart(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your shopping cart.")
        return redirect("user_homepage")

    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    cart_items = cart.items.select_related(
        "variant",
        "variant__product",
        "variant__color",
        "variant__size"
    ) if cart else []

    subtotal = cart.get_total_price if cart else Decimal('0')
    summary = calculate_checkout_summary(subtotal, Decimal('0'))
    
    any_out_of_stock = check_any_out_of_stock(cart_items)
    print(any_out_of_stock)
    
    context = {
        "cart": cart,
        "cart_items": cart_items,
        "delivery_charge": summary["delivery_charge"],
        "tax": summary["tax"],
        "grand_total": summary["grand_total"],
        "any_out_of_stock": any_out_of_stock,
    }
    return render(request, "cart/cart.html", context)


@login_required
@require_POST
def update_cart_quantity(request):
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    variant = cart_item.variant

    if not variant.is_active or variant.stock <= 0:
        return JsonResponse({
            "status": "error",
            "message": "This product is no longer available"
        }, status=400)

    if action == "increase":
        max_allowed = min(variant.stock, 5)
        if cart_item.quantity < max_allowed:
            cart_item.quantity += 1
            cart_item.save()
        else:
            if variant.stock < 5:
                if variant.stock == 1:
                    message = "Only 1 unit is available, which is already in your cart."
                else:
                    message = f"Only {variant.stock} units are available, and you've already added them all."
            else:
                message = "Maximum 5 units allowed per item."
            return JsonResponse({
                "status": "error",
                "message": message
            }, status=400)

    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()

    else:
        return JsonResponse({
            "status": "error",
            "message": "Invalid action"
        }, status=400)

    subtotal = cart_item.cart.get_total_price
    summary = calculate_checkout_summary(subtotal, Decimal('0'))

    any_out_of_stock = check_any_out_of_stock(cart_item.cart.items.all())

    return JsonResponse({
        "status": "success",
        "message": "Quantity updated",
        "data": {
            "quantity": cart_item.quantity,
            "item_subtotal": cart_item.sub_total,
            "item_base_subtotal": cart_item.base_sub_total,
            "subtotal": subtotal,
            "delivery_charge": float(summary["delivery_charge"]),
            "tax": float(summary["tax"]),
            "grand_total": float(summary["grand_total"]),
            "cart_count": cart_item.cart.total_items,
            "any_out_of_stock": any_out_of_stock,
            "item_stock": cart_item.variant.stock,
            "item_is_active": (
                cart_item.variant.is_active and 
                cart_item.variant.product.is_active and 
                cart_item.variant.product.category.is_active and 
                cart_item.variant.product.brand.is_active
            )
        }
    })


@login_required
@require_POST
def remove_cart_item(request):
    item_id = request.POST.get("item_id")

    if not item_id:
        return JsonResponse({
            "status": "error",
            "message": "Item ID is required"
        }, status=400)

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart = cart_item.cart
    cart_item.delete()

    subtotal = cart.get_total_price
    summary = calculate_checkout_summary(subtotal, Decimal('0'))

    return JsonResponse({
        "status": "success",
        "message": "Item removed from cart",
        "data": {
            "subtotal": subtotal,
            "delivery_charge": float(summary["delivery_charge"]),
            "tax": float(summary["tax"]),
            "grand_total": float(summary["grand_total"]),
            "cart_count": cart.total_items,
            "any_out_of_stock": check_any_out_of_stock(cart.items.all()),
        }
    })


# Initialize Razorpay Client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def validate_cart_items(request, cart_items):
    """Checks stock and calculates subtotal, total_discount, total_mrp"""
    total_mrp = 0
    total_discount = 0
    subtotal = 0

    for item in cart_items:
        variant = item.variant
        if (
            not variant.is_active or
            not variant.product.is_active or
            not variant.product.category.is_active or
            not variant.product.brand.is_active
        ):
            return None, f"{variant.product.name} is unavailable."

        if variant.stock <= 0:
            return None, f"{variant.product.name} is out of stock"

        if item.quantity > variant.stock:
            # Don't silently save, let the UI handle the "Only X left" warning
            pass

        pricing = variant.get_pricing_data()
        final_price = pricing["final_price"]

        total_mrp += variant.base_price * item.quantity
        subtotal += final_price * item.quantity
        total_discount += (variant.base_price - final_price) * item.quantity
    
    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "total_mrp": total_mrp
    }, None


def process_coupon_action(request, subtotal):
    """Handles coupon apply/remove requests and returns coupon_discount and applied_coupon or a redirect."""
    if request.method == "POST":
        if "apply_coupon" in request.POST:
            coupon_code = request.POST.get("coupon_code", "").strip().upper()
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                    is_valid, message = coupon.is_valid(subtotal, request.user)
                    if is_valid:
                        request.session["coupon_code"] = coupon.code
                        messages.success(request, "Coupon applied successfully!")
                    else:
                        messages.error(request, message)
                except Coupon.DoesNotExist:
                    messages.error(request, "Invalid coupon code.")
            return redirect("checkout")

        if "remove_coupon" in request.POST:
            request.session.pop("coupon_code", None)
            messages.success(request, "Coupon removed.")
            return redirect("checkout")

    coupon_code = request.session.get("coupon_code")
    coupon_discount = Decimal('0')
    applied_coupon = None

    if coupon_code:
        try:
            applied_coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            is_valid, message = applied_coupon.is_valid(subtotal, request.user)
            if is_valid:
                # We calculate the discount based on the subtotal (items price)
                # But it will be deducted from the grand total in calculate_checkout_summary
                coupon_discount = Decimal(str(applied_coupon.calculate_discount(subtotal)))
            else:
                request.session.pop("coupon_code", None)
                messages.error(request, f"Coupon removed: {message}")
                applied_coupon = None
        except Coupon.DoesNotExist:
            request.session.pop("coupon_code", None)
            
    return coupon_discount, applied_coupon


def calculate_checkout_summary(subtotal, coupon_discount):
    """Calculates tax, delivery, and grand total. Coupon is deducted from the final total."""
    tax_percentage = Decimal(str(settings.TAX_PERCENTAGE))
    tax = (subtotal * tax_percentage / Decimal('100')).quantize(Decimal('0.01'))
   
    if subtotal <= 0 or subtotal >= Decimal(str(settings.FREE_DELIVERY_THRESHOLD)):
        delivery_charge = Decimal('0')
    else:
        delivery_charge = Decimal(str(settings.DELIVERY_CHARGE))
        
    # Deduct coupon from the total of (subtotal + delivery + tax)
    pre_coupon_total = subtotal + delivery_charge + tax
    grand_total = max(pre_coupon_total - coupon_discount, Decimal('0'))
    
    return {
        "tax": tax,
        "delivery_charge": delivery_charge,
        "grand_total": grand_total
    }


def handle_cod_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, cart, applied_coupon):
    with transaction.atomic():
        order = create_order_instance(
            request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, "cod")
        finalize_order(order, cart_items, cart, applied_coupon)
    request.session.pop("coupon_code", None)
    return redirect("order_success", order_id=order.id)


def handle_wallet_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, cart, applied_coupon):
    wallet = request.user.wallet
    if wallet.balance >= grand_total:
        with transaction.atomic():
            wallet.deduct_funds(grand_total)
            order = create_order_instance(request, selected_address, subtotal, total_discount,
                                          coupon_discount, tax, grand_total, delivery_charge, "wallet", payment_status="paid")
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=grand_total,
                transaction_type='PAYMENT',
                description=f"Payment for Order #{order.orderid}"
            )
            finalize_order(order, cart_items, cart, applied_coupon)
        request.session.pop("coupon_code", None)
        messages.success(request, "Order placed successfully using Wallet!")
        return redirect("order_success", order_id=order.id)
    else:
        messages.error(request, "Insufficient wallet balance.")
        return None


def handle_razorpay_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, applied_coupon):
    razorpay_order = razorpay_client.order.create({
        "amount": int(grand_total * 100),
        "currency": "INR",
        "payment_capture": "1"
    })

    order = create_order_instance(request, selected_address, subtotal, total_discount,
                                  coupon_discount, tax, grand_total, delivery_charge, "razorpay")
    if applied_coupon:
        order.coupon = applied_coupon
        order.save()

    create_order_items(order, cart_items)

    razorpay_context = {
        "order": order,
        "razorpay_order_id": razorpay_order['id'],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": int(grand_total * 100),
    }
    return render(request, "cart/razorpay_checkout.html", razorpay_context)


@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user, is_active=True)
    cart_items = cart.items.select_related("variant", "variant__product", "variant__color", "variant__size")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart")

    # Validate Items & Prices
    pricing_data, error_message = validate_cart_items(request, cart_items)
    if error_message:
        messages.error(request, error_message)
        return redirect("cart")

    subtotal = pricing_data["subtotal"]
    total_discount = pricing_data["total_discount"]
    total_mrp = pricing_data["total_mrp"]

    # Handle Coupon (Apply/Remove)
    coupon_result = process_coupon_action(request, subtotal)
    if isinstance(coupon_result, HttpResponse):
        return coupon_result
    coupon_discount, applied_coupon = coupon_result

    # Calculate Summary
    summary = calculate_checkout_summary(subtotal, coupon_discount)
    tax = summary["tax"]
    delivery_charge = summary["delivery_charge"]
    grand_total = summary["grand_total"]

    # Handle Order Placement
    if request.method == "POST" and "place_order" in request.POST:
        address_id = request.POST.get("address_id")
        payment_method = request.POST.get("payment_method", "cod")

        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect("checkout")

        selected_address = get_object_or_404(UserAddress, id=address_id, user=request.user)

        if payment_method == "cod":
            return handle_cod_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, cart, applied_coupon)

        elif payment_method == "wallet":
            result = handle_wallet_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, cart, applied_coupon)
            return result if result else redirect("checkout")

        elif payment_method == "razorpay":
            return handle_razorpay_payment(request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, cart_items, applied_coupon)

    # 5. Render Checkout Page
    addresses = UserAddress.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    # Enhanced available coupons logic
    available_coupons_qs = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    )
    
    available_coupons = []
    for c in available_coupons_qs:
        is_valid, message = c.is_valid(subtotal, request.user)
        c.is_applicable = is_valid
        if not is_valid and c.minimum_amount > subtotal:
             c.eligibility_message = f"Add ₹{c.minimum_amount - subtotal} more to use this"
        else:
             c.eligibility_message = message
        available_coupons.append(c)

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "total_mrp": total_mrp,
        "subtotal":subtotal,
        "discount": total_discount,
        "coupon_discount": coupon_discount,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "grand_total": grand_total,
        "addresses": addresses,
        "default_address": default_address,
        "available_coupons": available_coupons,
        "applied_coupon_code": request.session.get("coupon_code"),
        "any_out_of_stock": check_any_out_of_stock(cart_items),
    }
    return render(request, "cart/checkout.html", context)

@csrf_exempt
@require_POST
@login_required
def payment_handler(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        order_internal_id = request.POST.get('order_internal_id')

        try:
            # Verify the authenticity of the payment signature
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            # Payment verified — check status strictly to avoid double processing
            with transaction.atomic():
                # Lock the order record
                order = Order.objects.select_for_update().get(id=order_internal_id)
                
                if order.payment_status == 'paid':
                    # Already processed by another request or thread
                    return redirect("order_success", order_id=order.id)

                if order.payment_status == 'refunded':
                    # Edge case: avoid processing if already refunded
                    return redirect("order_failure", order_id=order.id)

                cart = get_object_or_404(Cart, user=order.user, is_active=True)
                
                order.payment_status = 'paid'
                order.status = 'processing'
                order.save()
                complete_order_payment(order, order.coupon, cart)

            # Clean up coupon session
            request.session.pop('coupon_code', None)

            return redirect("order_success", order_id=order.id)

        except Exception:
            # Payment verification failed — mark order as failed if not already processed
            try:
                order = get_object_or_404(Order, id=order_internal_id)
                if order.payment_status not in ('paid', 'refunded'):
                    with transaction.atomic():
                        order.payment_status = 'failed'
                        order.status = 'failed'
                        order.save()
                        order.items.update(status='failed')
                return redirect("order_failure", order_id=order.id)
            except Exception:
                 return redirect("checkout")

    return redirect("checkout")

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "cart/order_success.html", {"order": order, "success_message": "Thank you for your purchase!"})

@login_required
def order_failure(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # Mark the order as failed if it's still pending (e.g. user dismissed the Razorpay modal)
    if order.payment_status in ('pending',) and order.payment_method == 'razorpay':
        order.payment_status = 'failed'
        order.status = 'failed'
        order.save()
        order.items.update(status='failed')
    return render(request, "cart/order_failure.html", {
        "order": order,
        "error_message": "Payment failed or was cancelled."
    })

@login_required
def retry_payment(request, order_id):
    """Retry Razorpay payment for a failed order."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Only allow retry for Razorpay orders with failed/pending payment
    if order.payment_method != 'razorpay':
        messages.error(request, "Retry is only available for online payments.")
        return redirect("order_history")

    if order.payment_status not in ('failed', 'pending'):
        messages.error(request, "This order cannot be retried.")
        return redirect("order_history")

    # Check stock availability for all order items
    for item in order.items.select_related('variant', 'variant__product'):
        if item.variant.stock < item.quantity:
            messages.error(
                request,
                f"{item.variant.product.name} does not have enough stock. Please place a new order."
            )
            return redirect("order_history")

    # Create a new Razorpay order for the same internal order
    razorpay_order = razorpay_client.order.create({
        "amount": int(order.total * 100),
        "currency": "INR",
        "payment_capture": "1"
    })

    razorpay_context = {
        "order": order,
        "razorpay_order_id": razorpay_order['id'],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": int(order.total * 100),
    }
    return render(request, "cart/razorpay_checkout.html", razorpay_context)
