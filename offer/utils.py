from django.utils import timezone
from .models import Offer

def get_best_offer(product):
    now = timezone.now()

    product_offers = Offer.objects.filter(
        offer_type='product',
        product=product,
        is_active=True,
        start_at_lte=now   
    ).exclude(end_at_lt=now)

    category_offers = Offer.objects.filter(
        offer_type='category',
        category=product.category,
        is_active=True,
        start_at__lte=now
    ).exclude(end_at__lt=now)

    all_offers = list(product_offers) + list(category_offers)

    if not all_offers:
        return None
    
    return max(all_offers,key=lambda offer:offer.discount_percentage)
    