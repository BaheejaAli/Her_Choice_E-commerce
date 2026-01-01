from django.shortcuts import render
from django.views.generic import TemplateView
from products.models import Product
from brandsandcategories.models import Category
from django.db.models import Q


# Create your views here.
class HomePageView(TemplateView):
    template_name = "user_section/homepage.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["new_arrivals"] = Product.objects.filter(is_active = True).order_by("-created_at")[:8]
        context["featured_products"] = Product.objects.filter(is_active=True, is_featured=True).order_by('?')[:6]
        context["categories"] = Category.objects.filter(is_active=True).order_by('?')[:4]
        context["trending_products"] = Product.objects.filter(is_most_demanded=True,is_active=True).order_by('?')[:8]

        return context

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)

    #     search_query = self.request.GET.get('search','').strip()
    #     active_products = Product.objects.filter(is_active = True)

    #     if search_query:
    #         context["search_results"] = active_products.filter(
    #             Q(name__icontains=search_query) |
    #             Q(category__name__icontains=search_query) |
    #             Q(brand__name__icontains=search_query)
    #         ).distinct()

    #     else:
    #         context["featured_products"] = Product.objects.filter(is_active=True, is_featured=True).order_by('?')[:6]
    #         context["trending_products"] = Product.objects.filter(is_active=True, is_most_demanded=True).order_by('?')[:4]
        
    #     context["categories"] = Category.objects.filter(is_active=True).order_by('?')[:4]
    #     context["search_query"] = search_query
    #     return context



