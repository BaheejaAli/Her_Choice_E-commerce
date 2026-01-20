from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from products.models import Product, ProductVariant
from .models import Cart, CartItem
from django.views.decorators.http import require_POST
from django.contrib import messages
from user_section.models import UserAddress, WishlistItem

# Create your views here.
@require_POST
@login_required
def add_to_cart(request):
    try:
        variant_id = request.POST.get("variant_id")
        # quantity = int(request.POST.get("quantity",1))

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

            # Remove from wishlist
            WishlistItem.objects.filter(wishlist__user = request.user, variant = variant).delete()

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

    cart = cart_item.cart
    cart_item.delete()

    return JsonResponse({
        "status": "success",
        "message": "Item removed from cart",
        "data": {
            "cart_total":cart.get_total_price
        }
    })

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user= request.user,is_active=True)
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
        
        if variant.stock <= 0 :
            messages.error(request, f"{variant.product.name} is out of stock")
            return redirect("cart")

        
        if item.quantity > variant.stock:
            item.quantity = variant.stock
            item.save(update_fields=["quantity"])

        total_mrp += variant.base_price * item.quantity
        total_discount += variant.discount_value * item.quantity
        subtotal += variant.final_price * item.quantity

    shipping_charge = 40 if subtotal > 0 else 0
    tax = 0           
    grand_total = subtotal + shipping_charge 
        
    # addresses = UserAddress.objects.filter(user=request.user)

    # default_address = addresses.filter(is_default=True).first()

    
    # if request.method == "POST":
    #     address_id = request.POST.get("address_id")
    #     payment_method = request.POST.get("payment_method","COD")
    #     if not address_id:
    #         messages.error(request, "Please select a delivery address.")
    #         return redirect("checkout")

    #     selected_address = get_object_or_404(
    #         UserAddress,
    #         id=address_id,
    #         user=request.user
    #     )


    context = {
        "cart": cart,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "discount": total_discount,
        "shipping": shipping_charge,
        "tax": tax,
        "grand_total": grand_total,
        # "addresses": addresses,
        # "default_address": default_address,
    }
    return render(request, "cart/checkout.html",context)

