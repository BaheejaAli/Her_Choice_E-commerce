from django.urls import path,include
from accounts.views import admin_auth
from . import views

urlpatterns = [

    path("", admin_auth.admin_login, name="admin_login"),
    path("dashboard/", views.admin_dashboard, name='admin_dashboard'),
    path("user-management/", views.user_management, name="user_management"),

    # new URL for blocking/unblocking a user
    path("toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),


]