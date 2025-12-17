from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.cache import never_cache 
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from brandsandcategories.models import Brand
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView,CreateView,UpdateView ,DeleteView
from brandsandcategories.forms import BrandForm
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from accounts.models import CustomUser

# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

# ============== ADMIN DASHBOARD ==================
@never_cache
def admin_dashboard(request):
    return render(request, "admin_panel/dashboard.html")


# ========= USER MANAGEMENT ==================
class UserListView(ListView):
    model = CustomUser
    template_name = 'admin_panel/user_management.html'
    context_object_name = 'users'
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            is_superuser=False,
            is_staff=False
        ).order_by('-date_joined')

        search_query = self.request.GET.get('q','').strip()
        status_filter = self.request.GET.get('status','')

        if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
        ).distinct()
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # pagination UI support
        paginator = context.get('paginator')
        page_obj = context.get('page_obj')
        if paginator and page_obj:
            context['page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=1,
                on_ends=1
            )

        
        base_qs = CustomUser.objects.filter(is_superuser=False, is_staff=False)
        context['total_users'] = base_qs.count()
        context['active_users'] = base_qs.filter(is_active=True).count()
        context['inactive_users'] = base_qs.filter(is_active=False).count()

        # Preserve filters
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')

        return context


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request,user_id):

    if request.method == 'POST':
        user_to_toggle = get_object_or_404(CustomUser, pk=user_id)

        if user_to_toggle == request.user:
            messages.error(request, "You cannot block or unblock your own account.")
            return redirect('user_management')
        
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save(update_fields=['is_active'])

        if user_to_toggle.is_active:
            messages.success(
                request, f"User {user_to_toggle.email} has been Unblocked."
            )
        else:
            messages.warning(
                request, f"User {user_to_toggle.email} has been Blocked."
            )

    return redirect('user_management')

# =========== Brand List View (Read) ===========
class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'admin_panel/brand_management.html'
    context_object_name = 'brands'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            product_count=Count('products', distinct=True)
        ).order_by('name')

        search_query = self.request.GET.get('q','').strip()
        status_filter = self.request.GET.get('status','')

        if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) 
            )

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BrandForm()   # for add or edit modal
        
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






