from django.shortcuts import render, get_object_or_404, redirect
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
from products.models import Product, ProductVariant, ProductVariantImage
from products.forms import ProductForm, ProductVariantForm, ProductVariantImageFormSet


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

# =========================
# ADMIN DASHBOARD
# =========================


@never_cache
@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
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

        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '')

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
def toggle_user_status(request, user_id):

    if request.method == 'POST':
        user_to_toggle = get_object_or_404(CustomUser, pk=user_id)

        if user_to_toggle == request.user:
            messages.error(
                request, "You cannot block or unblock your own account.")
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

        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '')

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
        context['current_status_filter'] = self.request.GET.get(
            'status', 'all')
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

    if brand.is_active:
        Product.objects.filter(
            brand=brand, category__is_active=True).update(is_active=True)
    else:
        Product.objects.filter(brand=brand).update(is_active=False)

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
        # messages.error(self.request, "Please fix the errors.")
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

        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '')

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

    def form_invalid(self, form):
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

    if category.is_active:
        Product.objects.filter(
            category=category, brand__is_active=True).update(is_active=True)
    else:
        Product.objects.filter(category=category).update(is_active=False)

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
@method_decorator([user_passes_test(is_admin), never_cache], name="dispatch")
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "admin_panel/product_management.html"
    context_object_name = "products"
    paginate_by = 5

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("category", "brand")
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


@login_required
@user_passes_test(is_admin)
@never_cache
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product created successfully.")
            return redirect("product_list")
    else:
        form = ProductForm()

    return render(request, "admin_panel/product_form.html", {"form": form})

# =============== Product Update View ===================


@login_required
@user_passes_test(is_admin)
@never_cache
def product_update(request, pk):
    product = Product.objects.select_related("category", "brand").get(pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)

    return render(request, "admin_panel/product_form.html", {"form": form, "product": product})


# =============== Toggle Product Status ===================
@require_POST
@login_required
@user_passes_test(is_admin, login_url='admin_login')
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])

    if not product.is_active:
        product.variants.update(is_active=False)

    return JsonResponse({
        'success': True,
        'is_active': product.is_active,
        'message': (
            f'Product "{product.name}" activated.'
            if product.is_active
            else f'Product "{product.name}" deactivated.'
        )
    })

# =============== Add product variant ===================

@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST,request.FILES)

        image_formset = ProductVariantImageFormSet(
                request.POST,
                request.FILES,
                prefix="images"
            )

        if form.is_valid() and image_formset.is_valid():
            uploaded_count = 0
            for f in image_formset:
                if f.cleaned_data.get("image") and not f.cleaned_data.get("DELETE"):
                    uploaded_count += 1

            if uploaded_count < 3:
                messages.error(
                    request,
                    f"You must upload at least 3 images. You uploaded {uploaded_count}."
                )
                return render(
                    request,
                    "admin_panel/product_variant_form.html",
                    {
                        "form": form,
                        "image_formset": image_formset,
                        "product": product,
                        "is_edit": False,
                    }
                )

            variant = form.save(commit=False)
            variant.product = product

            duplicate_exists = ProductVariant.objects.filter(
            product=product,
            color=variant.color,
            size=variant.size
            ).exists()

            if duplicate_exists:
                messages.error(request,"This variant with the same color and size already exists.")
                return render(request,"admin_panel/product_variant_form.html",
                    {
                        "form": form,
                        "image_formset": image_formset,
                        "product": product,
                        "is_edit": False,
                    }
                )

            if not variant.sku:
                variantSize = variant.size.id if variant.size else "FREESIZE"
                variantColor = variant.color.name.replace(" ", "").upper()
                variant.sku = f"{product.id}-{variantSize}-{variantColor}"
                
            variant.save()
            product.save(update_fields=["updated_at"])
            image_formset.instance = variant        
            image_formset.save()
            messages.success(request, "Product variant added successfully.")
            return redirect("product_list")

    else:
        form = ProductVariantForm()
        image_formset = ProductVariantImageFormSet(prefix="images")
        

    return render(
        request,
        "admin_panel/product_variant_form.html",
        {
            "form": form,
            "image_formset": image_formset,
            "product": product,
            "is_edit": False,
        }
    )


# =============== Product variant update ===================
@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_update(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    # product = variant.product

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        image_formset = ProductVariantImageFormSet(
            request.POST,
            request.FILES,
            instance=variant,
            prefix="images"
        )

        if form.is_valid() and image_formset.is_valid():
            deleted_forms = [
                f for f in image_formset
                if f.cleaned_data.get("DELETE")
            ]

            final_image_count = (
                variant.images.count()
                - len(deleted_forms)
                + len(request.FILES)
            )

            if final_image_count < 3:
                messages.error(
                    request,
                    "Variant must have at least 3 images."
                )
            else:
                with transaction.atomic():
                    form.save()
                    image_formset.save()
                    variant.product.save(update_fields=["updated_at"])

                messages.success(request, "Product variant updated successfully.")
                return redirect("product_list")
                # return redirect("product_variant_add", product_id=product.id)
        
    else:
        form = ProductVariantForm(instance=variant)
        image_formset = ProductVariantImageFormSet(instance=variant,prefix="images")

    return render(
        request,
        "admin_panel/product_variant_form.html",
        {
            "form": form,
            "image_formset": image_formset,
            "product": variant.product,
            "variant": variant,
            "is_edit": True,
        }
    )
# =============== Toggle product variant  ===================
@require_POST
@login_required
@user_passes_test(is_admin)
def toggle_variant_status(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if not variant.product.is_active:
        return JsonResponse({
            "success": False,
            "message": "Product is inactive"
        }, status=400)
    variant.is_active = not variant.is_active
    variant.save(update_fields=["is_active"])
    variant.product.save(update_fields=["updated_at"])


    return JsonResponse({
        "success": True,
        "is_active": variant.is_active,
        "message": (
            "Variant activated"
            if variant.is_active
            else "Variant deactivated"
        ),
    })



