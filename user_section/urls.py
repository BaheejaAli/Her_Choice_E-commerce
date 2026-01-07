from django.urls import path
from . import views
urlpatterns = [
    path("", views.HomePageView.as_view(), name="user_homepage"),
    path("profile_info/",views.profile_info, name="profile_info"),
    path("profile_info/edit",views.edit_profile, name="edit_profile"),
    path("profile_address/", views.profile_address, name= "profile_address"),
    
]
