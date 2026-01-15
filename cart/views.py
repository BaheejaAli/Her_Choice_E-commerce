from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from products.models import Product
from .models import Cart, CartItem
from django.views.decorators.http import require_POST
from django.contrib import messages
from user_section.models import UserAddress

# Create your views here.
@require_POST
@login_required
def add_to_cart(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")

        if not product_id:
            return JsonResponse({
                "status": "error",
                "message": "Product ID is required"}, status=400)

        product = get_object_or_404(Product, id=product_id)

        if not product.is_active or not product.category.is_active or not product.brand.is_active:
            return JsonResponse({
                "status": "error",
                "message": "This product is currently unavailable"
            }, status=400)

        # Stock check
        if product.stock <= 0:
            return JsonResponse({
                "status": "error",
                "message": "Product is out of stock",
            }, status=400)

        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": 1,
            }
        )

        if not created:
            if cart_item.quantity >= min(product.stock, 5):
                return JsonResponse({
                    "status": "error",
                    "message": "Stock limit reached",
                    "data": {
                        "available_stock": product.stock
                    }
                }, status=400)

            cart_item.quantity += 1
            cart_item.save()

        return JsonResponse({
            "status": "success",
            "message": "Product added to cart",
            "data": {
                "cart_count": cart.total_items,
                "product_id": product.id
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