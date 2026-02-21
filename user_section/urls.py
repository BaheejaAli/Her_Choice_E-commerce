from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.homepage, name="user_homepage"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("contact/", views.contact_page, name="contact"),
    path("product/", include('products.urls')),
    # path('product/<slug:slug>/', product_detail_view, name='product_detail'),
    
    path("profile-info/",views.profile_info, name="profile_info"),
    path("profile-info/edit/",views.edit_profile, name="edit_profile"),
    path("profile-info/upload-profile-pic/",views.upload_profile_pic, name="upload_profile_pic"),
    path("profile-address/", views.profile_address, name= "profile_address"),
    path("profile-address/add/", views.profile_add_address, name= "profile_add_address"),
    path("profile-address/edit/<int:address_id>/", views.profile_edit_address, name= "profile_edit_address"),
    path("profile-address/delete/<int:address_id>/", views.profile_delete_address, name= "profile_delete_address"),
    path("profile-change-password/",views.profile_change_password, name="profile_change_password"),
    path("profile-change-password/profile-otp-verify",views.profile_otp_verify, name="profile_otp_verify"),
    path("profile-change-password/profile-resend-otp",views.profile_resend_otp, name="profile_resend_otp"),


    path("cart/", include("cart.urls")),
    path("wishlist/",views.wishlist_view, name="wishlist_view"),
    path("wishlist/add/",views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/",views.remove_from_wishlist, name="remove_from_wishlist"),

    path("orders/",include("orders.urls")),
    path("wallet/",include("wallet.urls")),


    
]