from django.urls import path
from . import views
urlpatterns = [
    path("",views.home, name="home"),
    path("dashboard", views.admin_dashboard, name="admin_dashboard"),
    path("admin-logout/", views.admin_logout, name="admin_logout")
]
