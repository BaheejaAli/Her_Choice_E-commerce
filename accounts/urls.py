from django.urls import path
from .views import admin_auth,user_auth

urlpatterns = [
    # Admin Authentication URLs
    path("admin_login/", admin_auth.admin_login, name="admin_login"),
    path("admin_dashboard/", admin_auth.admin_dashboard, name="admin_dashboard"),
    path("admin_forgot-password/", admin_auth.admin_forgot_password, name="admin_forgot_password"),
    path("admin_otp_verify/", admin_auth.admin_otp_verify, name="admin_otp_verify"),
    path("admin_reset_password/", admin_auth.admin_reset_password, name="admin_reset_password"),
    path("admin_reset_success/", admin_auth.admin_reset_success, name="admin_reset_success")


]
