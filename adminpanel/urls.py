from django.urls import path
from . import views
from accounts.views import admin_auth
from .views import (
    BrandListView,
)

urlpatterns = [

    path("", admin_auth.admin_login, name="admin_login"),
    path("dashboard/", views.admin_dashboard, name='admin_dashboard'),

    path("users/", views.UserListView.as_view(), name="user_management"),
    path("toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),

    path("brand/", BrandListView.as_view(), name="brand_list"),


]