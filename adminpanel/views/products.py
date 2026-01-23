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
from products.models import Product, ProductVariant
from products.forms import ProductForm, ProductVariantForm, ProductVariantImageFormSet
from django.urls import reverse


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

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


@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        image_formset = ProductVariantImageFormSet(
            request.POST, request.FILES, prefix="images"
        )

        if form.is_valid() and image_formset.is_valid():
            uploaded_images = 0
            for f in image_formset:
                if f.cleaned_data.get("image") and not f.cleaned_data.get("DELETE"):
                    uploaded_images += 1

            if uploaded_images < 3:
                form.add_error(None, "At least 3 images are required to create a variant.")

            else:
                color = form.cleaned_data.get('color')
                size = form.cleaned_data.get('size')
                if ProductVariant.objects.filter(product=product, color=color, size=size).exists():
                    form.add_error(None, "At least 3 images are required to create a variant.")
                else:
                    with transaction.atomic():
                        variant = form.save(commit=False)
                        variant.product = product
                        
                        size_name = variant.size.name if variant.size else "FS"
                        variant.sku = f"{product.id}-{size_name}-{variant.color.name[:3].upper()}"
                        variant.save()

                        image_formset.instance = variant
                        image_formset.save()

                        product.save(update_fields=['updated_at'])

                    messages.success(request, "Variant and images added successfully.")
                    return redirect("product_list") 

    else:
        form = ProductVariantForm()
        image_formset = ProductVariantImageFormSet(prefix="images")

    return render(request, "admin_panel/product_variant_form.html", {
        "form": form,
        "image_formset": image_formset,
        "product": product,
        "is_edit": False,
    })

# ===============================
# EDIT VARIANT
# ===============================
@never_cache
@login_required
@user_passes_test(is_admin)
def product_variant_update(request, variant_id):
    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"),
        id=variant_id
    )
    product = variant.product
    form = ProductVariantForm(instance=variant)
    image_formset = ProductVariantImageFormSet(
        instance=variant,
        prefix="images"
    )
    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        image_formset = ProductVariantImageFormSet(
            request.POST,
            request.FILES,
            instance=variant,
            prefix="images"
        )
        print("\n========== DEBUG START ==========")
        print("FORM VALID:", form.is_valid())
        print("FORM ERRORS:", form.errors)
        print("FORM NON FIELD ERRORS:", form.non_field_errors())

        print("FORMSET VALID:", image_formset.is_valid())
        print("FORMSET ERRORS:", image_formset.errors)
        print("FORMSET NON FORM ERRORS:", image_formset.non_form_errors())

        print("TOTAL FORMS:", image_formset.total_form_count())
        print("INITIAL FORMS:", image_formset.initial_form_count())
        print("MIN NUM:", image_formset.min_num)

        for i, f in enumerate(image_formset):
            print(f"FORM {i} cleaned_data:", f.cleaned_data)

        print("=========== DEBUG END ===========\n")


        # -------------------------------
        # VALIDATION
        # -------------------------------
        if not form.is_valid() or not image_formset.is_valid():
            messages.error(request, "Please fix the errors below.")
            return render(
                request,
                "admin_panel/product_variant_form.html",
                {
                    "form": form,
                    "image_formset": image_formset,
                    "product": product,
                    "variant": variant,
                    "is_edit": True,
                }
            )

        # -------------------------------
        # IMAGE COUNT CHECK (FORMSET-BASED)
        # -------------------------------
        print("▶ CALCULATING FINAL IMAGE COUNT")

        final_image_count = 0
        for f in image_formset:
            print(
        "instance.pk:", f.instance.pk,
        "| image:", f.cleaned_data.get("image"),
        "| DELETE:", f.cleaned_data.get("DELETE")
    )
            if f.cleaned_data.get("DELETE"):
                continue
            if f.instance.pk or f.cleaned_data.get("image"):
                final_image_count += 1
        print("FINAL IMAGE COUNT:", final_image_count)


        if final_image_count < 3:
            messages.error(request, "Variant must have at least 3 images.")
            return render(
                request,
                "admin_panel/product_variant_form.html",
                {
                    "form": form,
                    "image_formset": image_formset,
                    "product": product,
                    "variant": variant,
                    "is_edit": True,
                }
            )

        # -------------------------------
        # SAVE (SUCCESS PATH)
        # -------------------------------
        print("💾 ABOUT TO SAVE VARIANT")

        with transaction.atomic():
            form.save()
            image_formset.save()
            product.save(update_fields=["updated_at"])

        messages.success(request, "Variant updated successfully.")
        print("➡️ REDIRECTING TO PRODUCT LIST")

        return redirect("product_list")

    # GET request
    return render(
        request,
        "admin_panel/product_variant_form.html",
        {
            "form": form,
            "image_formset": image_formset,
            "product": product,
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
