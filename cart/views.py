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
                    message = f"Only {variant.stock} unit{'s' if variant.stock != 1 else ''} available in stock."
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

    context = {
        "cart": cart,
        "cart_items": cart_items,
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
                message = f"Only {variant.stock} unit{'s' if variant.stock != 1 else ''} available in stock."
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

    return JsonResponse({
        "status": "success",
        "message": "Quantity updated",
        "data": {
            "quantity": cart_item.quantity,
            "item_subtotal": cart_item.sub_total,
            "item_base_subtotal": cart_item.base_sub_total,
            "cart_total": cart_item.cart.get_total_price,
            "cart_base_total": cart_item.cart.get_total_base_price
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

    return JsonResponse({
        "status": "success",
        "message": "Item removed from cart",
        "data": {
            "cart_total": cart.get_total_price
        }
    })


# Initialize Razorpay Client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def checkout(request):

    # FETCH CART & VALIDATE
    cart = get_object_or_404(Cart, user=request.user, is_active=True)
    cart_items = cart.items.select_related(
        "variant",
        "variant__product",
        "variant__color",
        "variant__size"
    )

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart")

    # CALCULATE BASE TOTALS
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
            messages.error(
                request,
                f"{variant.product.name} is unavailable."
            )
            return redirect("cart")

        if variant.stock <= 0:
            messages.error(request, f"{variant.product.name} is out of stock")
            return redirect("cart")

        if item.quantity > variant.stock:
            item.quantity = variant.stock
            item.save(update_fields=["quantity"])

        pricing = variant.get_pricing_data()
        final_price = pricing["final_price"]

        total_mrp += variant.base_price * item.quantity
        subtotal += final_price * item.quantity
        total_discount += (variant.base_price - final_price) * item.quantity

    # ---------HANDLE COUPON-------------
    coupon_discount = Decimal('0')
    applied_coupon = None
    # Apply coupon
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
    
        # Remove coupon
        if "remove_coupon" in request.POST:
            request.session.pop("coupon_code", None)
            messages.success(request, "Coupon removed.")
            return redirect("checkout")
    
    coupon_code = request.session.get("coupon_code")

    if coupon_code:
        try:
            applied_coupon = Coupon.objects.get(code=coupon_code)
            coupon_discount = Decimal(str(applied_coupon.calculate_discount(subtotal)))
        except Coupon.DoesNotExist:
            request.session.pop("coupon_code", None)   

    # FINAL TOTAL CALCULATION
    discounted_subtotal = max(subtotal - coupon_discount, Decimal('0'))
    tax_percentage = Decimal('5')
    tax = (discounted_subtotal * tax_percentage / Decimal('100')).quantize(Decimal('0.01'))
    if discounted_subtotal > Decimal('500'):
        delivery_charge = Decimal('0')
    else:
        delivery_charge = Decimal('40') 
    grand_total = discounted_subtotal + delivery_charge + tax
    

    # ORDER PLACEMENT
    if request.method == "POST" and "place_order" in request.POST:
        address_id = request.POST.get("address_id")
        payment_method = request.POST.get("payment_method", "cod")

        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect("checkout")

        selected_address = get_object_or_404(
            UserAddress,
            id=address_id,
            user=request.user
        )

        # CASH ON DELIVERY
        if payment_method == "cod":
            with transaction.atomic():
                order = create_order_instance(
                    request, selected_address, subtotal, total_discount, coupon_discount, tax, grand_total, delivery_charge, "cod")
                finalize_order(order, cart_items, cart, applied_coupon)
            request.session.pop("coupon_code", None)
            return redirect("order_success", order_id=order.id)

        # WALLET PAYMENT
        elif payment_method == "wallet":
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
                return redirect("checkout")

        # RAZORPAY PAYMENT
        elif payment_method == "razorpay":
            razorpay_order = razorpay_client.order.create({
                "amount": int(grand_total * 100),  # Amount in paise
                "currency": "INR",
                "payment_capture": "1"
            })

            # Create order WITH items upfront (no stock deduction yet)
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

    # CONTEXT FOR TEMPLATE
    addresses = UserAddress.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    )
    context = {
        "cart": cart,
        "cart_items": cart_items,
        "total_mrp": total_mrp,
        "discount": total_discount,
        "coupon_discount": coupon_discount,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "grand_total": grand_total,
        "addresses": addresses,
        "default_address": default_address,
        "available_coupons":available_coupons,
        "applied_coupon_code": coupon_code,
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

            # Payment verified — deduct stock and finalize
            order = get_object_or_404(Order, id=order_internal_id)
            cart = get_object_or_404(Cart, user=order.user, is_active=True)

            with transaction.atomic():
                order.payment_status = 'paid'
                order.status = 'processing'
                order.save()
                complete_order_payment(order, order.coupon, cart)

            # Clean up coupon session
            request.session.pop('coupon_code', None)

            return redirect("order_success", order_id=order.id)

        except Exception:
            # Payment verification failed — mark order as failed
            order = get_object_or_404(Order, id=order_internal_id)
            order.payment_status = 'failed'
            order.status = 'failed'
            order.save()
            order.items.update(status='failed')
            return redirect("order_failure", order_id=order.id)

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
