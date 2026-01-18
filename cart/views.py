from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from products.models import Product, ProductVariant
from .models import Cart, CartItem
from django.views.decorators.http import require_POST
from django.contrib import messages
from user_section.models import UserAddress

# Create your views here.
@require_POST
@login_required
def add_to_cart(request):
    variant_id = request.POST.get("variant_id")
    quantity = int(request.POST.get("quantity",1))

    if not variant_id:
        return JsonResponse({
            "status":"error",
            "message": "Variant ID is required"
        }, status = 400)
    
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
            "status" : "error",
            "message" : "Out of stock"
        })
    
    cart, _ = Cart.objects.get_or_create(user= request.user, is_active=True)
    cartItem, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity":1})

    if not created:
        if cartItem.quantity >= min(variant.stock, 5):
            return JsonResponse({
                "status": "error",
                "message": "Stock limit reached",
                "data": {   
                    "available_stock": variant.stock
                    }
                }, status=400)

        cartItem.quantity += 1
        cartItem.save(update_fields=["quantity"])

        return JsonResponse({
            "status": "success",
            "message": "Item added to cart successfully",
            "data": {
                "cart_count": cart.total_items,
            }
        }, status=200)


def cart(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to view your cart")
        return redirect("user_login")

    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    cart_items = cart.items.all() if cart else []
    context = {
        "cart": cart,
        "cart_items": cart_items,
    }
    return render(request, "cart/cart.html", context)


@login_required
def update_cart_quantity(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "invalid request"
        }, status=405)

    item_id = request.POST.get("item_id")
    action = request.POST.get("action")

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    product = cart_item.product
    if not product.is_active or product.stock <= 0:
        return JsonResponse({
            "status": "error",
            "message": "This product is no longer available"
        }, status=400)

    if action == "increase":
        if cart_item.quantity < min(cart_item.product.stock, 5):
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
            "cart_total": cart_item.cart.get_total_price
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

    cart_item.delete()

    return JsonResponse({
        "status": "success",
        "message": "Item removed from cart",
        "data": {
            "item_id": item_id,
            "cart_total":cart_item.cart.get_total_price
        }
    })

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user= request.user,is_active=True)
    cart_items = CartItem.objects.filter(cart=cart)

    addresses = UserAddress.objects.filter(user=request.user)

    if not cart_items.exists():
        return redirect("cart")
    
    context = {
        'cart_items' : cart_items,
        'total' : cart.get_total_price,
        'addresses' : addresses
    }
    return render(request, "cart/checkout.html",context)