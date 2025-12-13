from django.urls import path
from . import views
urlpatterns = [
    path("user-management/", views.user_management, name="user_management"),

    # new URL for blocking/unblocking a user
    path("user-management/toggle-status/<int:user_id>/", views.toggle_user_status, name="toggle_user_status"),
]