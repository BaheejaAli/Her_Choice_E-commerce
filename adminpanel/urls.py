from django.urls import path
from . import views
urlpatterns = [
    path("user-management/", views.user_management, name="user_management"),
]