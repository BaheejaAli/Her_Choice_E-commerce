from django.urls import path
from . import views
from products.views import ProductListingView
urlpatterns = [
    path("", views.HomePageView.as_view(), name="user_homepage"),
    path('shop/', ProductListingView.as_view(), name='product_listing'),
    # path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
]
