from offer.utils import get_best_offer

def apply_pricing(product, variants):

    offer = get_best_offer(product)
    product.active_offer = offer        # need if acitve offer in template 

    for variant in variants:
        if not variant.is_active:
            continue
        prices = [variant.base_price]
        discount_percentages = [0]

        if variant.sales_price and variant.base_price > 0:
            prices.append(variant.sales_price)
            sales_discount= int(((variant.base_price - variant.sales_price) / variant.base_price) * 100)
            discount_percentages.append(sales_discount)

        if offer and variant.base_price > 0:
            discount_amount = (variant.base_price * offer.discount_percentage) / 100
            offer_price = max(0,round(variant.base_price - discount_amount))
            offer_discount = offer.discount_percentage
            prices.append(offer_price)
            discount_percentages.append(offer_discount)

        variant.final_price = min(prices)
        variant.discount_percentage = max(discount_percentages)

def prepare_products_for_display(products):
    for product in products:
        variants = product.variants.all()

        apply_pricing(product, variants)

        active_variants = [v for v in variants if v.is_active]
        product.display_variant = active_variants[0] if active_variants else None

        product.display_image = None
        if product.display_variant:
            image = (
                product.display_variant.primary_image
                or product.display_variant.images.first()
            )
            if image:
                product.display_image = image.image