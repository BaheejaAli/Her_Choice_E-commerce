from django.shortcuts import render
from .models import Product, ProductVariant, Size, Review
from brandsandcategories.models import Category, Brand
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Case, When, F, DecimalField, Count, Min
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from products.utils import prepare_products_for_display
from user_section.models import WishlistItem
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


# -------------------------
# Product listing
# -------------------------
def product_listing(request):
    queryset = (
        Product.objects
        .filter(is_active=True, variants__is_active=True, variants__product__is_active=True, variants__stock__gt=0 )
        .select_related('category', 'brand')
        .distinct()
    )
    # .prefetch_related('variants__images')
    
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        queryset = queryset.filter(category_id__in=selected_categories)

    selected_brands = request.GET.getlist('brand')
    if selected_brands:
        queryset = queryset.filter(brand_id__in=selected_brands)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        ).distinct()

    sort_by = request.GET.get('sort', 'date_added')
    if sort_by == 'name_az':
        queryset = queryset.order_by('name')
    elif sort_by == 'name_za':
        queryset = queryset.order_by('-name')
    else:
        queryset = queryset.order_by('-created_at')
    
    # Pricing
    products = list(queryset)
    prepare_products_for_display(products)      

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:   
        products = [
            p for p in products 
            if p.display_variant and p.display_variant.final_price >= int(min_price)]

    if max_price:
        products = [
        p for p in products
        if p.display_variant and p.display_variant.final_price <= int(max_price)
        ]

    if sort_by == "price_low":
        products.sort(key=lambda p: p.display_variant.final_price)
    elif sort_by == "price_high":
        products.sort(key=lambda p: p.display_variant.final_price,reverse=True)
    
    if (min_price or max_price) and not products:
        messages.info(request, "No products found in this price range")

    paginator = Paginator(products, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('-product_count')

    brands = Brand.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ).order_by('-product_count')
    
    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        wishlist_variant_ids = set(
            WishlistItem.objects.filter(wishlist__user=request.user)
            .values_list('variant_id', flat=True)
        )

    context = {
        "products": page_obj,                   
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "page_range": paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        ),
        "query": search_query,
        "sort": sort_by,

        "categories": categories,
        "selected_categories": selected_categories,

        "brands": brands,
        "selected_brands": selected_brands,
        "wishlist_variant_ids": wishlist_variant_ids,
    }
    return render(request, "products/product_listing.html", context)


# -------------------------
# Product detail
# -------------------------
def product_detail_view(request, slug, sku=None):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    variants = (
        product.variants
        .filter(is_active=True)
        .select_related("color","size")
        .prefetch_related("images")
    )

    if not variants.exists():
        messages.warning(request, "Product unavailable")
        return redirect("user_homepage")

    if sku:
        selected_variant = variants.filter(sku=sku).first()
    else:
        selected_variant = variants.filter(stock__gt=0).first()

    if not selected_variant:
        messages.warning(request, "Variant not found")
        return redirect("product_listing")

   
    pricing = selected_variant.get_pricing_data()

    product.active_offer = pricing["active_offer"]
    
    color_variants = (variants.order_by("color_id","id").distinct("color_id"))
    sizes = Size.objects.filter(productvariant__product = product, productvariant__color= selected_variant.color).distinct()
    # Show related products that have active variants
    active_product_ids = ProductVariant.objects.filter(is_active=True, product__is_active=True).values_list('product_id', flat=True)
    
    related_products = (
        Product.objects
        .filter(category=product.category, is_active=True, id__in=active_product_ids)
        .exclude(id=product.id)
        .prefetch_related("variants__images")
        .order_by("-created_at")[:4]
    )
    prepare_products_for_display(related_products)


    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = WishlistItem.objects.filter(
            wishlist__user=request.user, 
            variant=selected_variant
        ).exists()

    context = {
        "product": product,
        "variants": variants,
        "selected_variant": selected_variant,  
        "color_variants": color_variants,      
        "sizes": sizes,    
        "related_products": related_products,
        "is_in_wishlist": is_in_wishlist,                     
    }

    return render(request, "products/product_detail.html", context)

@login_required
@require_POST
def add_review(request, product_id):
    
    product = get_object_or_404(Product, id=product_id)
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not rating:
        messages.error(request, "Please select a rating ")
        return redirect('product_detail', slug=product.slug)
    
    try:
        rating = int(rating)
    except ValueError:
        messages.error(request, "Invalid rating value")
        return redirect('product_detail', slug=product.slug)

    if rating not in [1, 2, 3, 4, 5]:
        messages.error(request, "Invalid rating value")
        return redirect('product_detail', slug=product.slug)
    
    review, created = Review.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={
            'rating': rating,
            'comment': comment
        }
    )

    if created:
        messages.success(request, "Review added successfully ")
    else:
        messages.success(request, "Your review has been updated ")
    return redirect('product_detail', slug=product.slug)