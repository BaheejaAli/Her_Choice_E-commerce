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
from .utils import create_order_instance, finalize_order
from decimal import Decimal
from wallet.models import WalletTransaction

# Create your views here.


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
            if cartItem.quantity >= min(variant.stock, 5):
                return JsonResponse({
                    "status": "error",
                    "message": "Maximum quantity reached",
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
        if cart_item.quantity < min(variant.stock, 5):
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({
                "status": "error",
                "message": "Maximum 5 units allowed."
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

    if subtotal > 500:
        delivery_charge = 0
    else:
        delivery_charge = 40 if subtotal > 0 else 0

    coupon_discount = 0
    applied_coupon = None

    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code.upper())
                is_valid, message = coupon.is_valid(subtotal)
                if is_valid:
                    coupon_discount = coupon.calculate_discount(subtotal)
                    grand_total -= coupon_discount
                    applied_coupon = coupon

                else:
                    messages.error(request, "Coupon is invalid.")
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code.")

    discounted_subtotal = subtotal - coupon_discount
    if discounted_subtotal < 0:
        discounted_subtotal = 0

    tax_percentage = 5
    tax = round((discounted_subtotal * tax_percentage) / 100, 2)

    grand_total = discounted_subtotal + delivery_charge + tax

    addresses = UserAddress.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "discount": total_discount,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "grand_total": grand_total,
        "addresses": addresses,
        "default_address": default_address,
    }
    
    if request.method == "POST":
        address_id = request.POST.get("address_id")
        payment_method = request.POST.get("payment_method", "COD")

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
            order = create_order_instance(request, selected_address, subtotal, total_discount,
                                          coupon_discount, tax, grand_total, delivery_charge, "razorpay")

            if applied_coupon:
                order.coupon = applied_coupon
                order.save()

            context.update({
                "order": order,
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": int(grand_total * 100),
            })
            return render(request, "cart/razorpay_checkout.html", context)

   
    return render(request, "cart/checkout.html", context)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
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
            
            # if success, update the order
            order = get_object_or_404(Order, id=order_internal_id)
            cart = get_object_or_404(Cart, user=order.user, is_active=True)
            cart_items = cart.items.all()
            
            with transaction.atomic():
                order.payment_status = 'paid'
                order.status = 'processing'
                order.save()
                finalize_order(order, cart_items, cart, order.coupon)
            
            return redirect("order_success", order_id=order.id)
            
        except Exception:
            # Handle verification failure
            order = get_object_or_404(Order, id=order_internal_id)
            order.payment_status = 'failed'
            order.status = 'failed'
            order.save()
            return redirect("order_failure", order_id=order.id)
            
    return redirect("checkout")

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "cart/order_success.html", {"order": order, "success_message": "Thank you for your purchase!"})


def order_failure(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "cart/order_failure.html", {
        "order": order,
        "error_message": "Payment failed or was cancelled."
    })
