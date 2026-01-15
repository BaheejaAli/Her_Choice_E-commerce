from django.urls import path
from . import views
from accounts.views import admin_auth
from .views import (
    BrandListView, BrandCreateView, BrandUpdateView,
    CategoryListView, CategoryCreateView, CategoryUpdateView,
    ProductListView
)

urlpatterns = [

    path("", admin_auth.admin_login, name="admin_login"),
    path("dashboard/", views.admin_dashboard, name='admin_dashboard'),

    path("users/", views.UserListView.as_view(), name="user_management"),
    path("users/toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),

    path("brands/", BrandListView.as_view(), name="brand_list"),
    path("brands/add/", BrandCreateView.as_view(), name="brand_add"),
    path("brands/<int:pk>/edit/", BrandUpdateView.as_view(), name="brand_edit"),  
    path('brands/toggle-status/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'),

    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("categories/add/", CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/toggle-status/<int:category_id>/", views.toggle_category_status, name="toggle_category_status"),

    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/add/",views.product_create, name="product_add"),
    path("products/<int:pk>/edit/",views.product_update, name="product_edit"),
    path("products/toggle-status/<int:product_id>/", views.toggle_product_status, name="toggle_product_status"),

    path("products/<int:product_id>/variants/add/",views.product_variant_add,name="product_variant_add"),
    path("variants/<int:variant_id>/edit/",views.product_variant_update,name="product_variant_edit"),
    path("variants/toggle-status/<int:variant_id>/",views.toggle_variant_status,name="toggle_variant_status"),


]