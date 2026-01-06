from django.urls import path
from . import views
from products.views import ProductListingView, product_detail_view
urlpatterns = [
    path("", views.HomePageView.as_view(), name="user_homepage"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path('shop/', ProductListingView.as_view(), name='product_listing'),
    path('product/<slug:slug>/', product_detail_view, name='product_detail'),
    
]
