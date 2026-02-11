from django.shortcuts import render, redirect
from accounts.forms import (UserRegistrationForm, UserLoginForm, UserForgotPasswordForm, UserResetPasswordForm,)
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser
import random
from datetime import timedelta
from django.utils import timezone
from accounts.utils import send_otp_email
from django.views.decorators.cache import never_cache
from accounts.decorators import logout_required
from allauth.socialaccount.providers.google.views import oauth2_callback

# Define the OTP expiry duration (e.g., 5 minutes)
OTP_EXPIRY_SECONDS = 100

# ========== USER REGISTRATION ======================
@never_cache
@logout_required(redirect_to="user_homepage")
def user_register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)

                user.is_active = False
                user.is_staff = False
                user.set_password(form.cleaned_data['password'])
                user.save()

                # Generate and Store OTP in session
                otp = random.randint(100000, 999999)
                request.session['verification_email'] = user.email
                request.session['verification_otp'] = str(otp)
                request.session['otp_expiry'] = (timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).timestamp()

                # SEND EMAIL 
                send_otp_email(user.email, otp, subject_prefix="Account Verification")

                messages.success(request, 'Registration successful. A verification code has been sent to your email.')
                return redirect('user_otp_verify')
            
            except IntegrityError:
                messages.error(request,'An account with this email already exists.')

            except Exception as e:
                print(f"Registration Error: {e}")
                messages.error(request, 'An unexpected error occurred during registration.')

    else:
        form = UserRegistrationForm()

    return render(request, "accounts/user_register.html", {'form':form})

# ========== USER LOGIN ======================
@never_cache
@logout_required(redirect_to="user_homepage")
def user_login(request):
    
    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, email=email, password=password)

            if user is not None:
                if user.is_active:
                    login(request,user)

                    if not user.has_seen_referral_page:
                        messages.info(request, "You can apply a referral code if you have one.")
                        return redirect('apply_referral_page')

                    messages.success(request, f"Welcome back, {user.first_name}!")
                    return redirect('user_homepage')
                
                else:
                    messages.warning(request, "Account not active.")
                    return redirect("user_login")
            else:
                error_message = "Invalid email or password."
                return render(request, 'accounts/user_login.html', {'form': form, 'error': error_message})

                    # if request.session.get('newly_verified'):
                    #     del request.session['newly_verified']
                    #     messages.success(request, f"Welcome {user.first_name}! Your account has been successfully created and verified.")            
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/user_login.html', {'form':form})

# ================== USER OTP VERIFICATION (Used after registration or password reset initiation) ==============
@never_cache
def user_otp_verify(request):
    verification_email = request.session.get('verification_email')
    stored_otp = request.session.get('verification_otp')
    otp_expiry = request.session.get('otp_expiry')

    if not verification_email:
        messages.error(request, 'Verification session expired or invalid.')
        return redirect('user_register') 
    
    if timezone.now().timestamp() > float(otp_expiry):
        messages.error(request, 'Verification code expired. Please resend.')
        # Clean up session data
        del request.session['verification_email']
        del request.session['verification_otp']
        del request.session['otp_expiry']
        return redirect('user_register')
    
    if request.method == 'POST':
        submitted_otp = request.POST.get('otp')

        if submitted_otp == stored_otp:
            try:
                # Activate the user account
                user = CustomUser.objects.get(email=verification_email)
                user.is_active = True
                user.save()
                
                # Clear OTP session data
                del request.session['verification_email']
                del request.session['verification_otp']
                del request.session['otp_expiry']

                # Mark as newly verified for special welcome message
                request.session['newly_verified'] = True

                messages.success(request, 'Email successfully verified. Welcome!')
                return redirect('user_login')
            
            except CustomUser.DoesNotExist:
                messages.error(request, 'User account not found.')
                return redirect('user_register')
            
        else:
            messages.error(request, 'Invalid verification code.')

    context = {
        'verification_email': verification_email,
        'otp_expiry': otp_expiry,
    }
    return render(request, 'accounts/user_otp_verify.html', context)

# ================== USER RESEND OTP VERIFICATION  ==============

@never_cache
def user_resend_otp(request):
    verification_email = request.session.get('verification_email')
    reset_email = request.session.get('reset_email')
    otp_expiry = request.session.get('otp_expiry')

    if otp_expiry:
        current_time = timezone.now().timestamp()
        if current_time < float(otp_expiry):
            messages.warning(request, "Please wait until timer expires.")

            if verification_email:
                return redirect('user_otp_verify')
            return redirect('user_reset_password_verify')
        
    if verification_email:
        target_email = verification_email
        session_otp_key = 'verification_otp'
        subject_prefix = "Registration Verification"
    elif reset_email:
        target_email = reset_email
        session_otp_key = 'reset_otp'
        subject_prefix = "Password Reset"
    else:
        messages.error(request, 'Session expired. Please restart.')
        return redirect('user_register')
    
    new_otp = random.randint(100000, 999999)
    request.session[session_otp_key] = str(new_otp)
    request.session['otp_expiry'] = (timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).timestamp()

    email_sent = send_otp_email(target_email, new_otp, subject_prefix=subject_prefix)

    if email_sent:
        messages.success(request, 'A new verification code has been successfully sent!')
    else:
        messages.error(request, 'Failed to send new code.')

    if verification_email:
        return redirect('user_otp_verify')
    return redirect('user_reset_password_verify')

# ================== USER FORGOT PASSWORD ========================
@never_cache
@logout_required(redirect_to="user_homepage")
def user_forgot_password(request):
    if request.method == 'POST':
        form = UserForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = CustomUser.objects.get(email=email)
                
                # Generate and store OTP/token for password reset
                reset_otp = random.randint(100000, 999999)
                request.session['reset_email'] = email
                request.session['reset_otp'] = str(reset_otp)
                request.session['otp_expiry'] = (timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).timestamp()
                
                # SEND EMAIL 
                email_sent = send_otp_email(email, reset_otp, subject_prefix="Password Reset")

                if email_sent:
                    messages.success(request, 'A password reset code has been sent to your email.')
                else:
                    # Security practice: Still show a success message but log/handle the failure
                    messages.error(request, 'If an account exists, a reset code has been sent, but there was an email error.')

                return redirect('user_reset_password_verify')

            except CustomUser.DoesNotExist:
                # Do not reveal if the email exists for security reasons
                messages.error(request, 'If an account exists, a reset code has been sent.')
                return redirect('user_forgot_password') 
    else:
        form = UserForgotPasswordForm()
    
    return render(request, 'accounts/user_forgot_password.html', {'form': form})


# ======================= PASSWORD RESET VERIFICATION (Reuse logic from OTP verify, but lead to password reset form) =====================
@never_cache
def user_reset_password_verify(request):
    reset_email = request.session.get('reset_email')
    stored_otp = request.session.get('reset_otp')
    otp_expiry = request.session.get('otp_expiry')

    if not reset_email:
        messages.error(request, 'Password reset session invalid.')
        return redirect('user_forgot_password') 

    # Check for OTP expiration
    if timezone.now().timestamp() > float(otp_expiry):
        messages.error(request, 'Reset code expired. Please try again.')
        # Clean up session data
        del request.session['reset_email']
        del request.session['reset_otp']
        del request.session['otp_expiry']
        return redirect('user_forgot_password')

    if request.method == 'POST':
        submitted_otp = request.POST.get('otp') 

        if submitted_otp == stored_otp:
            # OTP is correct. Set a flag to allow access to the actual reset form.
            request.session['otp_verified'] = True 
            
            # Clear OTP specific session data (keep reset_email)
            del request.session['reset_otp']
            del request.session['otp_expiry']
            
            messages.success(request, 'Verification successful. You can now set a new password.')
            return redirect('user_reset_password') # Redirect to the final reset form
        else:
            messages.error(request, 'Invalid verification code.')
    
    context = {
        'reset_email': reset_email,
        'otp_expiry': otp_expiry,
        # The template for this view will be the same as user_otp_verify.html, just pointing to this view's URL
    }
    return render(request, 'accounts/user_otp_verify.html', context) # Reusing the OTP template

# ===================== PASSWORD RESET FINAL STEP ==================
@never_cache
def user_reset_password(request):
    reset_email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')

    # Security check: Must have verified OTP to access this page
    if not reset_email or not otp_verified:
        messages.error(request, 'Access denied. Please verify your identity first.')
        return redirect('user_forgot_password')

    try:
        user = CustomUser.objects.get(email=reset_email)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('user_forgot_password')

    if request.method == 'POST':
        form = UserResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            # 1. Set the new password
            user.set_password(new_password)
            user.save()

            # 2. Clear all reset session data
            del request.session['reset_email']
            del request.session['otp_verified']
            
            # 3. Inform user and redirect to login
            messages.success(request, 'Your password has been reset successfully. Please log in.')
            return redirect('user_login')
    else:
        form = UserResetPasswordForm()
    
    return render(request, 'accounts/user_reset_password.html', {'form': form})


# ========== USER LOGOUT ======================
@login_required
@never_cache
def user_logout(request):
    logout(request)
    # messages.info(request, "You have been logged out successfully.")
    return redirect('user_login')


def google_callback_safe(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect("user_homepage")
    
    return oauth2_callback(request, *args, **kwargs)






