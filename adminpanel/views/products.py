from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from django.utils.decorators import method_decorator
from products.models import Product, ProductVariant, ProductVariantImage
from products.forms import ProductForm, ProductVariantForm
from django.urls import reverse


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

# =========== Product List View (Read) ===========
@method_decorator([login_required, user_passes_test(is_admin), never_cache], name="dispatch")
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

        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(brand__name__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context["page_range"] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=1,
                on_ends=1,
            )

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

# =============== Add Product Variant ===================
@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        files = request.FILES.getlist('variant_images')

        if form.is_valid():
            if len(files) < 3:
                form.add_error(None, "At least 3 images are required.")
            else:
                color = form.cleaned_data.get('color')
                size = form.cleaned_data.get('size')
                if ProductVariant.objects.filter(product=product, color=color, size=size).exists():
                    form.add_error(None, "A variant with this color and size already exists.")
                else:
                    try:
                        with transaction.atomic():
                            variant = form.save(commit=False)
                            variant.product = product
                            size_name = variant.size.name if variant.size else "FS"
                            variant.sku = f"{product.id}-{size_name}-{variant.color.name[:3].upper()}-{variant.color.id}"
                            variant.save()
                            
                            for i, f in enumerate(files):
                                ProductVariantImage.objects.create(
                                    variant=variant,
                                    image=f,
                                    is_primary=(i == 0)
                                )
                            product.save(update_fields=['updated_at'])
                        
                        messages.success(request, "Variant added successfully.")
                        return redirect("product_list")
                    except Exception as e:
                        form.add_error(None, f"Error saving variant: {str(e)}")
    else:
        form = ProductVariantForm()

    return render(request, "admin_panel/product_variant_form.html", {
        "form": form,
        "product": product,
        "is_edit": False,
    })

# =============== Edit Product Variant ===================
@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_update(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), id=variant_id)
    product = variant.product

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        new_files = request.FILES.getlist('variant_images')
        delete_ids = request.POST.getlist('delete_images')

        if form.is_valid():
            # Calculate final count
            existing_remaining = variant.images.exclude(id__in=delete_ids).count()
            total_count = existing_remaining + len(new_files)

            if total_count < 3:
                messages.error(request, "Variant must have at least 3 images.")
            else:
                try:
                    with transaction.atomic():
                        form.save()
                        if delete_ids:
                            ProductVariantImage.objects.filter(id__in=delete_ids, variant=variant).delete()
                        
                        for f in new_files:
                            ProductVariantImage.objects.create(variant=variant, image=f)
                            
                        if not variant.images.filter(is_primary=True).exists():
                            first_img = variant.images.first()
                            if first_img:
                                first_img.is_primary = True
                                first_img.save()

                        product.save(update_fields=["updated_at"])

                    messages.success(request, "Variant updated successfully.")
                    return redirect("product_list")
                except Exception as e:
                    messages.error(request, f"Error updating: {str(e)}")
    else:
        form = ProductVariantForm(instance=variant)

    return render(request, "admin_panel/product_variant_form.html", {
        "form": form,
        "product": product,
        "variant": variant,
        "is_edit": True,
    })


# =============== Toggle product variant status ===================
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
