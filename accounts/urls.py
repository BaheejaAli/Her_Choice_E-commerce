from django.urls import path
from django.shortcuts import render
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

    # User Authentication URLs
    path('user-register/', user_auth.user_register, name='user_register'),
    path('user-login/', user_auth.user_login, name='user_login'),
    path('user-logout/', user_auth.user_logout, name='user_logout'),

    # Verification and Reset
    path('user-verify-otp/', user_auth.user_otp_verify, name='user_otp_verify'),
    path('user-forgot-password/', user_auth.user_forgot_password, name='user_forgot_password'),
    path('user-reset-verify/', user_auth.user_reset_password_verify, name='user_reset_password_verify'),
    path('user-reset-password/', user_auth.user_reset_password, name='user_reset_password'),
    path('user-resend-otp/', user_auth.user_resend_otp, name='user_resend_otp'),
    

    # Dashboard/Protected View (Placeholder)
    path('dashboard/', lambda request: render(request, 'accounts/user_dashboard.html'), name='user_dashboard'),
]


