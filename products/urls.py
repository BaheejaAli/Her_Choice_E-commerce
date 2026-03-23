from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_listing, name='product_listing'),
    path('detail/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('detail/<slug:slug>/variant/<str:sku>/', views.product_detail_view, name='product_detail_variant'),
    path('add-review/<int:product_id>/', views.add_review, name='add_review'),
    
]