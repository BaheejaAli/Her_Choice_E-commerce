from django.shortcuts import render
from django.views.generic import ListView
from .models import Product
from brandsandcategories.models import Category, Brand
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Case, When, F, DecimalField, Count, Min
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
# Create your views here.

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
    product = get_object_or_404(Product, slug=slug)
    if not product.is_active:
        messages.warning(request, "This product is currently unavailable.")
        return redirect('product_listing')

    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).prefetch_related('images')[:4]

    context = {
        'product': product,
        'related_products': related_products,
    }

    return render(request, "products/product_detail.html", context)
