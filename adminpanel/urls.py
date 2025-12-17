from django.urls import path
from . import views
from accounts.views import admin_auth
from .views import (
    BrandListView, BrandCreateView, BrandUpdateView
)

urlpatterns = [

    path("", admin_auth.admin_login, name="admin_login"),
    path("dashboard/", views.admin_dashboard, name='admin_dashboard'),

    path("users/", views.UserListView.as_view(), name="user_management"),
    path("users/toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),

    path("brand/", BrandListView.as_view(), name="brand_list"),
    path('brands/toggle-status/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'),
    path("brands/add/", BrandCreateView.as_view(), name="brand_add"),
    path("brands/edit/<int:pk>/", BrandUpdateView.as_view(), name="brand_edit"),  

]