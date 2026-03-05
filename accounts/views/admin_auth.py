from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from accounts.forms import AdminLoginForm, AdminForgotPasswordForm, AdminResetPasswordForm 
from accounts.models import CustomUser
from django.contrib.auth.hashers import make_password
from accounts.utils import send_otp_email
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import random, time
from django.contrib import messages

# Create your views here.

# ================== Admin Login (Authentication) ==================
@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")
    
    if request.method == "POST":
        form = AdminLoginForm(request.POST) 
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, email=email, password=password)

            if user is not None and user.is_staff:
                login(request, user)
                return redirect("admin_dashboard")
            else:
                return render(
                    request,
                    "accounts/admin_login.html",
                    {"form": form, "error": "Invalid admin credentials"},
                )
        else:
            return render(
                request,
                "accounts/admin_login.html",
                {"form": form}
            )

    else:
        form = AdminLoginForm()

    return render(request, "accounts/admin_login.html", {"form": form})

# ================== Admin Forgot Password ==================
@never_cache
def admin_forgot_password(request):
    if request.method == "POST":
        form = AdminForgotPasswordForm(request.POST) 
        
        if form.is_valid():
            email = form.cleaned_data.get("email") 

            try:
                user = CustomUser.objects.get(email=email, is_staff=True)
            except CustomUser.DoesNotExist:
                return render(
                    request,
                    "accounts/admin_forgot_password.html",
                    {"form": form, "error": "Email not found"}, 
                )

            otp = random.randint(100000, 999999)

            request.session["reset_email"] = email
            request.session["reset_otp"] = str(otp)
            request.session["otp_timestamp"] = time.time()

            send_otp_email(email, otp)

            return redirect("admin_otp_verify")

        else:
            return render(
                request, 
                "accounts/admin_forgot_password.html", 
                {"form": form}
            )
            
    else:
        form = AdminForgotPasswordForm() 

    return render(request, "accounts/admin_forgot_password.html", {"form": form})

# ================== Admin OTP Verification ==================
@never_cache
def admin_otp_verify(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("reset_otp")
        timestamp = request.session.get("otp_timestamp")

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
@never_cache
def admin_reset_password(request):
    if not request.session.get("otp_verified"):
        return redirect("admin_otp_verify")

    if request.method == "POST":
        form = AdminResetPasswordForm(request.POST) 
        
        if form.is_valid():
            new_password = form.cleaned_data.get("new_password")
            email = request.session.get("reset_email") 

            try:
                user = CustomUser.objects.get(email=email)
                user.password = make_password(new_password)
                user.save()
            except CustomUser.DoesNotExist:
                 return redirect("admin_forgot_password")

            request.session.pop("reset_email", None)
            request.session.pop("reset_otp", None)
            request.session.pop("otp_verified", None)
            request.session.pop("otp_timestamp", None)

            return redirect("admin_reset_success")
        else:
            return render(request, "accounts/admin_reset_password.html", {"form": form})

    else:
        form = AdminResetPasswordForm() 

    return render(request, "accounts/admin_reset_password.html", {"form": form})

# ================== Admin Reset Password Success ==================
@never_cache
def admin_reset_success(request):
    return render(request, "accounts/admin_reset_success.html")

# ================== Admin Logout ==================
@login_required
def admin_logout(request):
    logout(request)
    return redirect("admin_login")

# ================== Admin Dashboard ==================
@login_required
@never_cache
def admin_dashboard(request):
    if not (request.user.is_active and request.user.is_staff):
        return redirect("admin_login")

    return render(request, "accounts/admin_dashboard.html")

