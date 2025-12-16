from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.cache import never_cache

# Create your views here.
def home(request):
    return render(request, "frontend_pages/user/homepage.html")

# # ----------------- Custom Test Function -----------------
# def is_admin(user):
#     """
#     Checks if the user is active AND has staff status.
#     This ensures they are logged in and authorized for the admin site.
#     """
#     return user.is_active and user.is_staff

# ----------------- Protected View -----------------
# because is_admin implicitly checks if the user object exists (i.e., is authenticated)


