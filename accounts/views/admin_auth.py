from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from accounts.forms import AdminLoginForm, AdminForgotPasswordForm, AdminResetPasswordForm 
from accounts.models import CustomUser
from django.contrib.auth.hashers import make_password
from accounts.utils import send_otp_email
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import random, time

# Create your views here.

# ================== Admin Login (Authentication) ==================
@never_cache
def admin_login(request):
    # CHECK IF USER IS ALREADY LOGGED IN AND IS AN ADMIN
    if request.user.is_authenticated and hasattr(request.user, 'is_admin') and request.user.is_admin:
        # If the user is already authenticated AND is an admin, redirect to dashboard
        return redirect("admin_dashboard")
    
    if request.method == "POST":
        form = AdminLoginForm(request.POST) # <--- Using the Form
        if form.is_valid():
            # Get clean data from the form
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            remember_me = form.cleaned_data.get("remember")

            user = authenticate(request, email=email, password=password)

            if user is not None and user.is_staff:
                login(request, user)

                if not remember_me:
                    request.session.set_expiry(0)
                return redirect("admin_dashboard")
            else:
                return render(
                    request,
                    "accounts/admin_login.html",
                    {"form": form, "error": "Invalid admin credentials"},
                )
        else:
            # If form is invalid (e.g., bad email format)
            return render(
                request,
                "accounts/admin_login.html",
                {"form": form}
            )

    else:
        form = AdminLoginForm() # Initialize empty form for GET request

    return render(request, "accounts/admin_login.html", {"form": form})

# ================== Admin Forgot Password ==================
# Handles admin forgot password by checking if the email exists
def admin_forgot_password(request):
    if request.method == "POST":
        form = AdminForgotPasswordForm(request.POST) # <--- Using the Form
        
        if form.is_valid():
            email = form.cleaned_data.get("email") # <--- Safe, cleaned data

            # Check if the user exists AND is an admin
            try:
                user = CustomUser.objects.get(email=email, is_admin=True)
            except CustomUser.DoesNotExist:
                return render(
                    request,
                    "accounts/admin_forgot_password.html",
                    {"form": form, "error": "Email not found"}, # Pass form back with error
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

        else:
            # If form is invalid (e.g., email format is wrong)
            return render(
                request, 
                "accounts/admin_forgot_password.html", 
                {"form": form}
            )
            
    else:
        form = AdminForgotPasswordForm() # Initialize empty form for GET request

    return render(request, "accounts/admin_forgot_password.html", {"form": form})

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
            return redirect("admin_reset_password")

        return render(
            request,
            "accounts/admin_otp_verify.html",
            {"error": "Invalid OTP. Please try again."},
        )
    return render(request, "accounts/admin_otp_verify.html")


# ================== Admin Reset Password ==================
def admin_reset_password(request):
    # Ensure OTP was verified before resetting password 
    if not request.session.get("otp_verified"):
        return redirect("admin_otp_verify")

    if request.method == "POST":
        form = AdminResetPasswordForm(request.POST) 
        
        if form.is_valid():
            new_password = form.cleaned_data.get("new_password")
            email = request.session.get("reset_email") 

            # Update password in database
            try:
                user = CustomUser.objects.get(email=email)
                user.password = make_password(new_password)
                user.save()
            except CustomUser.DoesNotExist:
                 # Should not happen if flow is correct, but safe check
                 return redirect("admin_forgot_password")

            # Clear session
            request.session.pop("reset_email", None)
            request.session.pop("reset_otp", None)
            request.session.pop("otp_verified", None)
            request.session.pop("otp_timestamp", None)

            return redirect("admin_reset_success")
        else:
             # If form is invalid (passwords don't match, or fail validation)
            return render(request, "accounts/admin_reset_password.html", {"form": form})

    else:
        form = AdminResetPasswordForm() # Initialize empty form for GET request

    return render(request, "accounts/admin_reset_password.html", {"form": form})

# ================== Admin Reset Password Success ==================
def admin_reset_success(request):
    return render(request, "accounts/admin_reset_success.html")

# ================== Admin Logout ==================
def admin_logout(request):
    logout(request)
    return redirect("admin_login")

# ================== Admin Dashboard ==================
@login_required
@never_cache
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect("admin_login")

    return render(request, "accounts/admin_dashboard.html")
