from django.urls import path
from accounts.views import admin_auth
from .views.dashboard import admin_dashboard
from .views.users import UserListView, toggle_user_status
from .views.brands import (
    BrandListView, BrandCreateView, BrandUpdateView,toggle_brand_status)
from .views.categories import (
    CategoryListView, CategoryCreateView, CategoryUpdateView,toggle_category_status)
from .views.products import (
    ProductListView,product_create, product_update, toggle_product_status, product_variant_add,product_variant_update,toggle_variant_status)
from .views.orders import order_management,update_order_status, order_view_details
urlpatterns = [

    path("", admin_auth.admin_login, name="admin_login"),
    path("dashboard/", admin_dashboard, name='admin_dashboard'),

    path("users/", UserListView.as_view(), name="user_management"),
    path("users/toggle-status/<int:user_id>/", toggle_user_status, name="toggle_user_status"),

    path("brands/", BrandListView.as_view(), name="brand_list"),
    path("brands/add/", BrandCreateView.as_view(), name="brand_add"),
    path("brands/<int:pk>/edit/", BrandUpdateView.as_view(), name="brand_edit"),  
    path('brands/toggle-status/<int:brand_id>/', toggle_brand_status, name='toggle_brand_status'),

    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("categories/add/", CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/toggle-status/<int:category_id>/", toggle_category_status, name="toggle_category_status"),

    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/add/",product_create, name="product_add"),
    path("products/<int:pk>/edit/",product_update, name="product_edit"),
    path("products/toggle-status/<int:product_id>/", toggle_product_status, name="toggle_product_status"),

    path("products/<int:product_id>/variants/add/",product_variant_add,name="product_variant_add"),
    path("variants/<int:variant_id>/edit/", product_variant_update,name="product_variant_edit"),
    path("variants/toggle-status/<int:variant_id>/", toggle_variant_status,name="toggle_variant_status"),

    path("orders/",order_management, name="order_management"),
    path("orders/update-status/<int:order_id>/", update_order_status, name="update_order_status"),
    path("orders/view-details/<int:order_id>/", order_view_details, name="order_view_details")

    

]