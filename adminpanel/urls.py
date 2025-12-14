from django.urls import path,include
from . import views

app_name = 'adminpanel'
urlpatterns = [

    path("", views.admin_root_redirect, name="admin_root_redirect"),
    path("", include('frontend_pages.urls')),
    path('brandsandcategories/', include(('brandsandcategories.urls', 'brandsandcategories'), namespace='brandsandcategories')),

    path("user-management/", views.user_management, name="user_management"),

    # new URL for blocking/unblocking a user
    path("user-management/toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),


]