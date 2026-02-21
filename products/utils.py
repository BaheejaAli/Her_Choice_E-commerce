from offer.utils import get_best_offer

def prepare_products_for_display(products):
    for product in products:
        offer = get_best_offer(product)
        product.active_offer = offer

        # pick first active variant WITH stock, or fallback to first active
        variant = product.variants.filter(is_active=True, stock__gt=0).first()
        if not variant:
            variant = product.variants.filter(is_active=True).first()

        if not variant:
            product.display_variant = None
            product.display_image = None
            continue

        # attach pricing to VARIANT
        pricing = variant.get_pricing_data(offer)

        variant.final_price = pricing["final_price"]
        variant.discount_percentage = pricing["discount_percentage"]

        product.display_variant = variant

        # image
        img = variant.primary_image or variant.images.first()
        product.display_image = img.image if img else None

    return products
