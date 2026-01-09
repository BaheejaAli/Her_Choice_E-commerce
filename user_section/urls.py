from django.urls import path
from . import views
from products.views import ProductListingView, product_detail_view

urlpatterns = [
    path("", views.HomePageView.as_view(), name="user_homepage"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path('shop/', ProductListingView.as_view(), name='product_listing'),
    path('product/<slug:slug>/', product_detail_view, name='product_detail'),
    
    path("profile-info/",views.profile_info, name="profile_info"),
    path("profile-info/edit/",views.edit_profile, name="edit_profile"),
    path("profile-info/upload-profile-pic/",views.upload_profile_pic, name="upload_profile_pic"),
    path("profile-address/", views.profile_address, name= "profile_address"),
    path("profile-ddress/add/", views.profile_add_address, name= "profile_add_address"),
    path("profile-address/edit/<int:address_id>/", views.profile_edit_address, name= "profile_edit_address"),
    path("profile-address/delete/<int:address_id>/", views.profile_delete_address, name= "profile_delete_address"),
    
]