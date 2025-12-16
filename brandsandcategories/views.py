from django.shortcuts import redirect, get_object_or_404
from .models import Brand
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView,CreateView,UpdateView ,DeleteView
from django.contrib.auth.decorators import login_required
from .forms import BrandForm
from django.urls import reverse_lazy
from django.db.models import Count
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q

# Create your views here.
# =========== Brand List View (Read) ===========

class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'brandsandcategories/admin_brand.html'
    context_object_name = 'brands'

    paginate_by = 10
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by(*self.ordering)
        queryset = queryset.annotate(
            product_count=Count('products', distinct=True) 
        )
        status_filter = self.request.GET.get('status')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BrandForm() 
        
        # Pass back current filter and search values to pre-fill the form/inputs
        context['current_status_filter'] = self.request.GET.get('status', 'all')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context

# ============== Brand Create View ===================
class BrandCreateView(LoginRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm 
    template_name = 'adminpanel/brands/admin_brand.html' 
    success_url = reverse_lazy('brandsandcategories:brands_list') 

# ================== Brand Update View =================
class BrandUpdateView(LoginRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'adminpanel/brands/admin_brand.html' 
    context_object_name = 'brand' 
    success_url = reverse_lazy('brandsandcategories:brands_list')

# =============== Brand Delete View ===================
class BrandDeleteView(LoginRequiredMixin, DeleteView):
    model = Brand
    template_name = 'adminpanel/brands/admin_brand.html' 
    context_object_name = 'brand'
    success_url = reverse_lazy('brandsandcategories:brands_list')

# =============== Toggle Brand Status ===================

@require_POST
@login_required 
def toggle_brand_status(request, pk):
    """
    View to securely toggle the active status of a brand by flipping its current state.
    This eliminates redundant status checking from the HTML template.
    """
    try:
        brand = get_object_or_404(Brand, pk=pk)
        brand.is_active = not brand.is_active
        brand.save()
        status_text = "activated (Restored)" if brand.is_active else "deactivated (Soft Deleted)"
        return JsonResponse({
            'success': True,
            'status_text': status_text,
            'new_status_bool': brand.is_active,
            'message': f'Brand "{brand.name}" status successfully set to {status_text}.',
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: Could not update status. {str(e)}',
        }, status=400)

