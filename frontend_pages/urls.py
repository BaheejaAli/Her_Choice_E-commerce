from django.urls import path
from . import views
app_name = 'frontend_pages'
urlpatterns = [
    path("",views.home, name="home"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    
]
