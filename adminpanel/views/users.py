from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from django.db.models import Q

from django.utils.decorators import method_decorator
from accounts.models import CustomUser


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

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


