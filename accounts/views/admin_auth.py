from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from accounts.models import CustomUser
from django.contrib.auth.hashers import make_password
from accounts.utils import send_otp_email
import random, time

# Create your views here.


# ================== Admin Login (Authentication) ==================
def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_admin:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            return render(
                request,
                "accounts/admin_login.html",
                {"error": "Invalid admin credentials"},
            )

    return render(request, "accounts/admin_login.html")


# ================== Admin Forgot Password ==================
# Handles admin forgot password by checking if the email exists
def admin_forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if the user exists AND is an admin
        try:
            user = CustomUser.objects.get(email=email, is_admin=True)
        except CustomUser.DoesNotExist:
            return render(
                request,
                "accounts/admin_forgot_password.html",
                {"error": "Email not found"},
            )

        # ----- Generate 6-digit OTP -----
        otp = random.randint(100000, 999999)

        # Save OTP + email in session
        request.session["reset_email"] = email
        request.session["reset_otp"] = str(otp)
        request.session["otp_timestamp"] = time.time()

        # Send OTP Email
        send_otp_email(email, otp)

        # Redirect to OTP verify page
        return redirect("admin_otp_verify")

    return render(request, "accounts/admin_forgot_password.html")


# ================== Admin OTP Verification ==================
# Verifies the OTP entered by the admin during password reset.
def admin_otp_verify(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("reset_otp")
        timestamp = request.session.get("otp_timestamp")

        # Check for OTP validity
        if not saved_otp or not timestamp or (time.time() - timestamp) > 300: # 300 seconds = 5 minutes
            return render(
                request,
                "accounts/admin_otp_verify.html",
                {"error": "OTP expired or not requested. Please try again."},
            )

        if entered_otp == saved_otp:
            request.session["otp_verified"] = True
            # print("the items are",request.session.items())
            return redirect("admin_reset_password")

        return render(
            request,
            "accounts/admin_otp_verify.html",
            {"error": "Invalid OTP. Please try again."},
        )
    return render(request, "accounts/admin_otp_verify.html")


# ================== Admin Reset Password ==================
# Allows the admin to create a new password after OTP verification.
def admin_reset_password(request):
    # Ensure OTP was verified before resetting password
    if not request.session.get("otp_verified"):
        return redirect("admin_otp_verify")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        email = request.session.get("reset_email")

        # empty fields check
        if not new_password or not confirm_password:
            return render(request, "accounts/admin_reset_password.html", {
                "error": "Password fields cannot be empty"
            })
        
        # ----- Password Strength Validation -----
        if len(new_password) < 8:
            return render(
                request,
                "accounts/admin_reset_password.html",
                {"error": "Password must be at least 8 characters long."},
            )

        # Passwords must match
        if new_password != confirm_password:
            return render(
                request,
                "accounts/admin_reset_password.html",
                {"error": "Passwords do not match"},
            )

        # Update password in database
        user = CustomUser.objects.get(email=email)
        user.password = make_password(new_password)
        user.save()

        # Clear session
        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)
        request.session.pop("otp_verified", None)
        request.session.pop("otp_timestamp", None)

        return redirect("admin_reset_success")

    return render(request, "accounts/admin_reset_password.html")


# ================== Admin Reset Password Success ==================
def admin_reset_success(request):
    return render(request, "accounts/admin_reset_success.html")

# ================== Admin Logout ==================
def admin_logout(request):
    logout(request)
    return redirect("admin_login")

# ================== Admin Dashboard ==================
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect("admin_login")

    return render(request, "accounts/dashboard.html")
