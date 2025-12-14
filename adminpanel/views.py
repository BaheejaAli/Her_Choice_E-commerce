from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.cache import never_cache 
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage
from django.urls import reverse

# NEW IMPORTS FOR SEARCH AND PAGINATION
from django.db.models import Q


# Create your views here.

# ============== ADMIN DASHBOARD ==================

def admin_root_redirect(request):
    # this redirect admin_panel to admin_dashboard
    return redirect(reverse('frontend_pages:admin_dashboard'))










# ========= USER MANAGEMENT ==================

# Get the active User model
User = get_user_model()

# check if a user is an admin/staff
def is_admin(user):
    return user.is_active and (user.is_staff or user.is_superuser)

@never_cache
@login_required
@user_passes_test(is_admin)
def user_management(request):
    # --- Search Logic ---
    search_query = request.GET.get('q')
    user_list = User.objects.all().order_by('-date_joined')         # Sorting by latest joined (descending)

    if search_query:                                                # Filter users based on your CustomUser model fields
        user_list = user_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        ).distinct()
    
    # --- FILTER LOGIC ---
    status_filter = request.GET.get('status_filter', 'all')

    print(f"DEBUG: Status filter received: '{status_filter}'")

    if status_filter == 'active':
        user_list = user_list.filter(is_active = True)
    elif status_filter == 'inactive':
        user_list = user_list.filter(is_active = False)

    # Pagination
    PAGINATE_BY = 10 
    paginator = Paginator(user_list, PAGINATE_BY)   # The Paginator SLICES 'user_list'
    page_number = request.GET.get('page', 1)    # 'page_obj' contains ONLY the 10 users for the current page

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'search_query': search_query or '',
        'status_filter': status_filter,
    }
    return render(request, "admin_panel/user_management.html",context)

# active/inactive user in user management
@login_required
@user_passes_test(is_admin)
def toggle_user_status(request,user_id):
    # Ensure the action is triggered by POST for security
    if request.method == 'POST':
        user_to_toggle = get_object_or_404(User, pk=user_id)

        # Admins cannot block themselves
        if user_to_toggle == request.user:
            messages.error(request, "You cannot block or unblock your own account.")
            return redirect('user_management')

        # Toggle the status
        if user_to_toggle.is_active:
            user_to_toggle.is_active = False # Block the user
            messages.warning(request, f"User {user_to_toggle.email} has been Blocked.")
        else:
            user_to_toggle.is_active = True # Unblock the user
            messages.success(request, f"User {user_to_toggle.email} has been Unblocked.")

        user_to_toggle.save()
    return redirect('adminpanel:user_management')




