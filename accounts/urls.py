from django.urls import path
from .views import admin_auth,user_auth

urlpatterns = [
    # Admin Authentication URLs
    path("admin-login/", admin_auth.admin_login, name="admin_login"),
    path("admin-dashboard/", admin_auth.admin_dashboard, name="admin_dashboard"),
    path("admin-forgot-password/", admin_auth.admin_forgot_password, name="admin_forgot_password"),
    path("admin-otp-verify/", admin_auth.admin_otp_verify, name="admin_otp_verify"),
    path("admin-reset-password/", admin_auth.admin_reset_password, name="admin_reset_password"),
    path("admin-reset-success/", admin_auth.admin_reset_success, name="admin_reset_success"),
    path("admin-logout/", admin_auth.admin_logout, name="admin_logout"),

]
