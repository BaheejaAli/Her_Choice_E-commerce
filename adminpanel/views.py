from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.cache import never_cache  
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView    
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db import transaction
from django.utils.decorators import method_decorator
from accounts.models import CustomUser
from brandsandcategories.models import Brand, Category 
from brandsandcategories.forms import BrandForm, CategoryForm
from products.models import Product
from products.forms import ProductForm, ProductImageFormSet


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

# ========================= 
# ADMIN DASHBOARD 
# =========================
@never_cache
@login_required(login_url='admin_login')
@user_passes_test(is_admin,login_url='admin_login')
def admin_dashboard(request):
    return render(request, "admin_panel/dashboard.html")


# ========================
# USER MANAGEMENT
# ========================
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class UserListView(LoginRequiredMixin, ListView):
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


# ========= USER TOGGLE STATUS(BLOCK/UNBLOCK) ==================
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


# ========================
# BRAND MANAGEMENT
# ========================

# =========== Brand List View (Read) ===========
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'admin_panel/brand_management.html'
    context_object_name = 'brands'
    paginate_by = 5
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            product_count=Count('products', distinct=True)
        ).order_by('-updated_at')

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

        # pagination UI support
        paginator = context.get('paginator')
        page_obj = context.get('page_obj')
        if paginator and page_obj:
            context['page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=1,
                on_ends=1
            )
        
        # Pass back current filter and search values to pre-fill the form/inputs
        context['current_status_filter'] = self.request.GET.get('status', 'all')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context

# =============== Toggle Brand Status ===================
@require_POST
@login_required
@user_passes_test(is_admin, login_url='admin_login')
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)

    brand.is_active = not brand.is_active
    brand.save(update_fields=['is_active'])

    return JsonResponse({
        'success': True,
        'is_active': brand.is_active,
        'message': (
            f'Brand "{brand.name}" activated.'
            if brand.is_active
            else f'Brand "{brand.name}" deactivated.'
        )
    })

# =============== Brand Update View ===================
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class BrandUpdateView(LoginRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html' 
    context_object_name = 'brand' 
    success_url = reverse_lazy('brand_list')

    def form_valid(self, form):
        messages.success(self.request, "Brand updated successfully.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors.")
        return self.render_to_response(self.get_context_data(form=form)) 

# ============== Brand Create View ===================
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class BrandCreateView(LoginRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html' 
    success_url = reverse_lazy('brand_list') 

    def form_valid(self, form):
        messages.success(self.request, "Brand created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))
    


# ========================
# CATEGORY MANAGEMENT
# ========================

# =========== Category List View (Read) ===========
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'admin_panel/category_management.html'
    context_object_name = 'categories'
    paginate_by = 5
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            product_count=Count('products', distinct=True)
        ).order_by('-updated_at')

        search_query = self.request.GET.get('q','').strip()
        status_filter = self.request.GET.get('status','')

        if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                  Q(description__icontains=search_query) 
            )

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CategoryForm() 

        # pagination UI support
        paginator = context.get('paginator')
        page_obj = context.get('page_obj')
        if paginator and page_obj:
            context['page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=1,
                on_ends=1
            )
        
        # Pass back current filter and search values to pre-fill the form/inputs
        context['current_status_filter'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context
    
# ============== Category Create View ===================
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_panel/category_form.html' 
    success_url = reverse_lazy('category_list') 

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully.")
        return super().form_valid(form)

    def form_invalid(self,form):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))

# =============== Category Update View ===================
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_panel/category_form.html' 
    context_object_name = 'category' 
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors.")
        return self.render_to_response(self.get_context_data(form=form)) 


# =============== Toggle Category Status ===================
@require_POST
@login_required
@user_passes_test(is_admin, login_url='admin_login')
def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])

    return JsonResponse({
        'success': True,
        'is_active': category.is_active,
        'message': (
            f'Category "{category.name}" activated.'
            if category.is_active
            else f'Category "{category.name}" deactivated.'
        )
    })


# ========================
# PRODUCT MANAGEMENT
# ========================

# =========== Product List View (Read) ===========
@method_decorator([user_passes_test(is_admin),never_cache],name="dispatch")
class ProductListView(LoginRequiredMixin,ListView):
    model = Product
    template_name = "admin_panel/product_management.html"
    context_object_name = "products"
    paginate_by = 5
     
    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("category", "brand")
            .annotate(image_count=Count("images", distinct=True))
            .order_by("-updated_at")
        )

        search_query = self.request.GET.get("q", "").strip()
        status_filter = self.request.GET.get("status", "")

        # Status filter
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

        # Search filter
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(brand__name__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Pagination UI support
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context["page_range"] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=1,
                on_ends=1,
            )

        # Preserve filters
        context["current_status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")

        return context

# ============== Product Create View =================== 
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')
class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin_panel/product_form.html'
    success_url = reverse_lazy('product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES)
        else:
            context['image_formset'] = ProductImageFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if image_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()  # Save Product first
                image_formset.instance = self.object    #Link Parent to Children
                image_formset.save()       # Save the 3+ images
            messages.success(self.request, "Product and 3 images uploaded successfully.")
            return super().form_valid(form)
        else:
            # If image_formset is invalid, re-render the form with errors
            return self.render_to_response(self.get_context_data(form=form))

# =============== Product Update View ===================   
@method_decorator([user_passes_test(is_admin), never_cache], name='dispatch')  
class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """
    Handles the logic for updating existing product details
    and managing the associated image formset.
    """
    model = Product
    form_class = ProductForm
    template_name = 'admin_panel/product_form.html'
    success_url = reverse_lazy('product_list')

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'brand').prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(
                self.request.POST, 
                self.request.FILES, 
                instance=self.object
            )
        else:
            context['image_formset'] = ProductImageFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if image_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                image_formset.instance = self.object
                image_formset.save()
            messages.success(self.request, "Product updated successfully.")
            return super().form_valid(form)
        else:
            print("Formset Errors:", image_formset.errors)
        return self.form_invalid(form)
    

# =============== Toggle Product Status ===================
@require_POST
@login_required
@user_passes_test(is_admin, login_url='admin_login')
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])

    return JsonResponse({
        'success': True,
        'is_active': product.is_active,
        'message': (
            f'Product "{product.name}" activated.'
            if product.is_active
            else f'Product "{product.name}" deactivated.'
        )
    })


