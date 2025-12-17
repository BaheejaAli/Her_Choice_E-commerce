from django.urls import path
from . views import BrandCreateView, BrandUpdateView, BrandDeleteView, toggle_brand_status


urlpatterns = [
    # path('brands/add/', BrandCreateView.as_view(), name='brand_add'),
    # path('brands/<int:pk>/edit/', BrandUpdateView.as_view(), name='edit_brand'),
    # path('brands/<int:pk>/delete/', BrandDeleteView.as_view(), name='delete_brand'),
    # path('brands/toggle-status/<int:brand_id>/', toggle_brand_status, name='toggle_brand_status'),
]