from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_listing, name='product_listing'),
    path('detail/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path("api/variant/",views.variant_detail_api,name="variant_detail_api"),


]