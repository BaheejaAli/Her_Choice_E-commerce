from django.shortcuts import render
from .models import Product, ProductVariant, Size
from brandsandcategories.models import Category, Brand
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Case, When, F, DecimalField, Count, Min
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse

#  only one image
def attach_display_image(products):
    for product in products:
        product.display_image = None

        variant = product.variants.filter(is_active=True).first()
        if not variant:
            continue

        image = variant.images.filter(is_primary=True).first()
        if image:
            product.display_image = image.image


def product_listing(request):
    queryset = (
        Product.objects
        .filter(is_active=True, variants__is_active=True)
        .select_related('category', 'brand')
    )
    queryset =queryset.annotate(
        selling_price=Min(
            Case(
                When(
                    variants__offer_price__isnull=False,
                    then=F('variants__offer_price')
                ),
                default=F('variants__base_price'),
                output_field=DecimalField()
            )
        )
    ).distinct()

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

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        queryset = queryset.filter(selling_price__gte=min_price)
    if max_price:
        queryset = queryset.filter(selling_price__lte=max_price)

    sort_by = request.GET.get('sort', 'date_added')
    if sort_by == 'price_low':
        queryset = queryset.order_by('selling_price')
    elif sort_by == 'price_high':
        queryset = queryset.order_by('-selling_price')
    elif sort_by == 'name_az':
        queryset = queryset.order_by('name')
    elif sort_by == 'name_za':
        queryset = queryset.order_by('-name')
    else:
        queryset = queryset.order_by('-created_at')

    paginator = Paginator(queryset, 12)  # 12 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for product in page_obj:
        product.display_variant = product.variants.filter(is_active=True).first()

    attach_display_image(page_obj)


    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('-product_count')

    brands = Brand.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ).order_by('-product_count')
    
    context = {
        "products": page_obj,                   
        "page_obj": page_obj,                   
        "search_query": search_query,
        "current_sort": sort_by,

        "categories": categories,
        "selected_categories": selected_categories,

        "brands": brands,
        "selected_brands": selected_brands,
    }
    return render(request, "products/product_listing.html", context)

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    variants = (
        product.variants
        .filter(is_active=True)
        .select_related("color", "size")
        .prefetch_related("images")
    )

    if not variants.exists():
        messages.warning(request, "Product unavailable")
        return redirect("product_listing")
    
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        color_id = request.GET.get("color")
        size_id = request.GET.get("size")

        variant = variants.filter(
            color_id=color_id,
            size_id=size_id
        ).first()

        if not variant:
            return JsonResponse({"success": False}, status=404)

        return JsonResponse({
            "success": True,
            "variant": {
                "id": variant.id,
                "price": str(variant.offer_price or variant.base_price),
                "stock": variant.stock,
                "images": [img.image.url for img in variant.images.all()],
            }
        })



    variant_id = request.GET.get("variant")
    color_id = request.GET.get("color")
    size_id = request.GET.get("size")

    selected_variant = None

   
    if variant_id:
        selected_variant = variants.filter(id=variant_id).first()

    if not selected_variant and color_id and size_id:
        selected_variant = variants.filter(
            color_id=color_id,
            size_id=size_id
        ).first()

    if not selected_variant and color_id:
        selected_variant = variants.filter(color_id=color_id).first()

    if not selected_variant:
        selected_variant = variants.first()

    color_variant_ids = (
        variants
        .values("color_id")
        .annotate(variant_id=Min("id"))
        .values_list("variant_id", flat=True)
    )

    color_variants = (
    variants
    .order_by("color_id", "id")  
    .distinct("color_id")         
)

    size_ids = (
        variants
        .filter(color=selected_variant.color)
        .values_list("size_id", flat=True)
        .distinct()
    )

    sizes = Size.objects.filter(id__in=size_ids)

    context = {
        "product": product,
        "variants": variants,
        "selected_variant": selected_variant,  
        "color_variants": color_variants,      
        "sizes": sizes,                       
    }

    return render(request, "products/product_detail.html", context)

def variant_detail_api(request):
    variant_id = request.GET.get("variant_id")

    if not variant_id:
        return JsonResponse({"error": "variant_id required"}, status=400)

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        is_active=True
    )

    images = [
        img.image.url
        for img in variant.images.all()
    ]

    return JsonResponse({
        "variant_id": variant.id,
        "price": str(variant.final_price),
        "base_price": str(variant.base_price),
        "offer_price": str(variant.offer_price) if variant.offer_price else None,
        "stock": variant.stock,
        "size": variant.size.name if variant.size else None,
        "images": images
    })