from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.cache import never_cache 
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from adminpanel.utils import get_pagination


# NEW IMPORTS FOR SEARCH AND PAGINATION
from django.db.models import Q


# Create your views here.

# ============== ADMIN DASHBOARD ==================
@never_cache
def admin_dashboard(request):
    return render(request, "admin_panel/dashboard.html")


# ========= USER MANAGEMENT ==================

# Get the active User model
User = get_user_model()

# check if a user is an admin/staff
# def is_admin(user):
#     return user.is_active and (user.is_staff or user.is_superuser)

@never_cache
@login_required
# @user_passes_test(is_admin)
def user_management(request):
    
    search_query = request.GET.get('q', '').strip()
    
    #query to exclude staffs and superusers
    users = User.objects.filter(is_superuser=False, is_staff=False).order_by('-date_joined')   

    if search_query:                                                
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        ).distinct()
    
    # --- FILTER LOGIC ---
    status_filter = request.GET.get('status_filter', '').strip()

    if status_filter == 'active':
        users = users.filter(is_active = True)
    elif status_filter == 'inactive':
        users = users.filter(is_active = False)

    page_obj = get_pagination(request, users, per_page=5)

    context = {
        'page_obj': page_obj,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(), 
        'inactive_users': User.objects.filter(is_active=False).count(),
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, "admin_panel/user_management.html",context)

# active/inactive user in user management
@login_required
# @user_passes_test(is_admin)
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
    return redirect('user_management')




