from django.urls import path
from . views import BrandListView, BrandCreateView, BrandUpdateView, BrandDeleteView, toggle_brand_status

app_name = 'brandsandcategories' 

urlpatterns = [
    # BRAND URLS
    path("brands/", BrandListView.as_view(), name="brands_list"),
    path('brands/add/', BrandCreateView.as_view(), name='brand_add'),
    path('brands/<int:pk>/edit/', BrandUpdateView.as_view(), name='edit_brand'),
    path('brands/<int:pk>/delete/', BrandDeleteView.as_view(), name='delete_brand'),
    path('brands/<int:pk>/toggle-status/', toggle_brand_status, name='toggle_brand_status'),
]