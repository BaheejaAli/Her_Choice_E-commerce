from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

@never_cache
@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def admin_dashboard(request):
    return render(request, "admin_panel/dashboard.html")

