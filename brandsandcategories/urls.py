from django.urls import path
from . import views

app_name = 'brandsandcategories' 

urlpatterns = [
    # BRAND URLS
    path("brands/", views.BrandListView.as_view(), name="brands_list"),
    path('brands/add/', views.BrandCreateView.as_view(), name='brand_add'),
    # path('brands/edit/', views.edit_brand, name='edit_brand'),
    # path('brands/delete/<int:brand_id>/', views.delete_brand, name='delete_brand'),
    
    # ... other brand URLs (detail, toggle-status, bulk-actions, export) ...

    # CATEGORY URLS (TBA)
    # path('categories/', views.category_list, name='category_list'),
]