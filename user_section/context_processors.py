from cart.models import Cart
from .models import Wishlist

def cart_wishlist_counts(request):
    if request.user.is_authenticated:
        cart  = Cart.objects.filter(user=request.user,is_active=True).first()
        cart_count = cart.total_items if cart else 0

        wishlist = Wishlist.objects.filter(user=request.user).first()
        wishlist_count = wishlist.items.count() if wishlist else 0
        
        return {
            'cart_count': cart_count,
            'wishlist_count': wishlist_count
        }
    return {'cart_count': 0, 'wishlist_count': 0}
