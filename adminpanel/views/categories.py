from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from brandsandcategories.models import Category
from brandsandcategories.forms import CategoryForm
from products.models import Product



# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

# =========== Category List View (Read) ===========
@method_decorator([login_required, user_passes_test(is_admin), never_cache], name='dispatch')
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


@method_decorator([login_required, user_passes_test(is_admin), never_cache], name='dispatch')
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


@method_decorator([login_required, user_passes_test(is_admin), never_cache], name='dispatch')
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

