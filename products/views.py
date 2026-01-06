from django.shortcuts import render
from django.views.generic import ListView, DetailView
from .models import Product
from brandsandcategories.models import Category, Brand
from django.db.models import Q
from django.db.models import Case, When, F, DecimalField, Count
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
# Create your views here.

class ProductListingView(ListView):
    model = Product
    template_name = "products/product_listing.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active = True)

        # queryset for sorting based on the selling price
        queryset = queryset.annotate(
            selling_price=Case(
                When(offer_price__gt=0, then=F('offer_price')),
                default=F('base_price'),
                output_field=DecimalField(),
            )
        )

        # Category filter logic
        selected_categories = self.request.GET.getlist('category')
        if selected_categories:
            queryset = queryset.filter(category_id__in=selected_categories)

        # Brand filter logic
        selected_brands = self.request.GET.getlist('brand')
        if selected_brands:
            queryset = queryset.filter(brand_id__in=selected_brands)

        search_query = self.request.GET.get('search','').strip()
        if search_query:       
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(brand__name__icontains=search_query) |
                Q(category__name__icontains=search_query)
            ).distinct()

        # price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(selling_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(selling_price__lte=max_price)

        # sorting logic
        sort_by = self.request.GET.get('sort', 'date_added') # Default to newest

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
        return queryset
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get('search','').strip()
        context["current_sort"] = self.request.GET.get('sort', 'newest')

        context["categories"] = Category.objects.annotate(
            product_count = Count('products', filter=Q(products__is_active = True))       
            ).order_by('-product_count')                                            # to display categories
        context["selected_categories"] = self.request.GET.getlist('category')       # to maintain checkbox checks

        context["brands"] = Brand.objects.annotate(
            product_count = Count('products', filter=Q(products__is_active = True))
        ).order_by('-product_count')
        context["selected_brands"] = self.request.GET.getlist('brand')
        return context
    

# class ProductDetailView(DetailView):
#     model = Product
#     template_name = "products/product_detail.html"
#     context_object_name = "product"
#     slug_url_kwarg = 'slug'

#     def get(self, request, *args, **kwargs):

#         # Redirect if product is blocked/unavailable
#         product = self.get_object()
#         if not product.is_active:
#             messages.warning(request,"This product is currently unavailable.")
#             return redirect('product_listing')
#         return super().get(request, *args, **kwargs)
    
#     def get_context_data(self, **kwargs):
#             # Related product recommendations
#             context = super().get_context_data(**kwargs)
#             context["related_products"] = Product.objects.filter(
#                 category= self.object.category, is_active = True
#             ).exclude(id=self.object.id).prefetch_related('images')[:4]
#             return context
        
def product_detail_view(request,slug):
    product = get_object_or_404(Product,slug=slug)
    if not product.is_active:
        messages.warning(request, "This product is currently unavailable.")
        return redirect('product_listing')
    
    related_products = Product.objects.filter(
        category = product.category,
        is_active = True
    ).exclude(id=product.id).prefetch_related('images')[:4]

    context = {
        'product':product,
        'related_products':related_products,
    }

    return render(request, "products/product_detail.html", context)

  
    