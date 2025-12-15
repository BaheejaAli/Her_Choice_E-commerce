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

# Create your views here.
# =========== Brand List View (Read) ===========

class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'brandsandcategories/admin_brand.html'
    context_object_name = 'brands'

    paginate_by = 10
    ordering = ['name']

    # Inject the creation form into the context for the modal
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BrandForm() 
        return context
    
    # def get_queryset(self):
    #     return Brand.objects.annotate(
    #         category_count=Count('categories', distinct=True),
    #         product_count=Count('products', distinct=True)
    #     )

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
        status_action = "activated (Restored)" if brand.is_active else "deactivated (Soft Deleted)"
        messages.success(request, f'Brand "{brand.name}" status successfully {status_action}.')
        
    except Exception as e:
        messages.error(request, f'An error occurred: Could not update status. {str(e)}')
    return redirect('brandsandcategories:brands_list')

