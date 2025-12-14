from django.shortcuts import render
from .models import Brand
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView,CreateView,UpdateView ,DeleteView
from .forms import BrandForm
from django.urls import reverse_lazy

# Create your views here.
# =========== Brand List View (Read) ===========

class BrandListView(LoginRequiredMixin, ListView):
    # Displays a list of all existing Brand objects.
    model = Brand
    template_name = 'brandsandcategories/admin_brand.html'
    context_object_name = 'brands'

    paginate_by = 10
    ordering = ['name']

    # Inject the creation form into the context for the modal
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Assuming BrandForm exists and is imported
        context['form'] = BrandForm() 
        return context

# --- 2. Brand Create View ---
class BrandCreateView(LoginRequiredMixin, CreateView):
    # Handles the creation of a new brand, usually triggered by the "Add New Brand" modal form.
    model = Brand
    form_class = BrandForm # Use the dedicated form class
    template_name = 'adminpanel/brands/admin_brand.html' # Often uses the list template for modal forms
    success_url = reverse_lazy('brandsandcategories:brands_list') 

# --- 3. Brand Update View ---
class BrandUpdateView(LoginRequiredMixin, UpdateView):
    # Handles displaying a pre-filled form and updating an existing brand.
    model = Brand
    form_class = BrandForm
    template_name = 'adminpanel/brands/admin_brand.html' # Or a dedicated form template
    context_object_name = 'brand' 
    success_url = reverse_lazy('brandsandcategories:brands_list')
    # Note: This view uses 'pk' (primary key) from the URL to identify the brand to update.

# --- 4. Brand Delete View ---
class BrandDeleteView(LoginRequiredMixin, DeleteView):
    # Handles the confirmation and deletion of a brand.
    model = Brand
    # Use a minimal template for confirmation, or skip template rendering entirely for AJAX
    template_name = 'adminpanel/brands/brand_confirm_delete.html' 
    context_object_name = 'brand'
    success_url = reverse_lazy('brandsandcategories:brands_list')
    # Note: This view also uses 'pk' from the URL.

