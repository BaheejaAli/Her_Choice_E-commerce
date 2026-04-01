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
from django.views.decorators.http import require_POST
from offer.models import Referral, ReferralUsage, ReferralReward
from django.db import transaction
from django.db.models import F

# Define the OTP expiry duration(5 minutes)
OTP_EXPIRY_SECONDS = 100

# ========== USER REGISTRATION ======================
@never_cache
@logout_required(redirect_to="user_homepage")
def user_register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                existing_user = CustomUser.objects.filter(email=email, is_active=False).first()
                if existing_user:
                    user = existing_user
                    user.set_password(password)
                    user.first_name = form.cleaned_data.get('first_name', user.first_name)
                    user.save()
                
                else:
                    user = form.save(commit=False)
                    user.is_active = False
                    user.is_staff = False
                    user.set_password(form.cleaned_data['password'])
                    user.save()

                otp = random.randint(100000, 999999)
                request.session['verification_email'] = user.email
                request.session['verification_otp'] = str(otp)
                request.session['otp_expiry'] = (timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).timestamp()

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

                    messages.success(request, f"Welcome back, {user.first_name}!")
                    return redirect('user_homepage')
                
                else:
                    messages.warning(request, "Account not active.")
                    return redirect("user_login")
            else:
                error_message = "Invalid email or password."
                return render(request, 'accounts/user_login.html', {'form': form, 'error': error_message})

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
    
    if not otp_expiry or timezone.now().timestamp() > float(otp_expiry):
        messages.error(request, 'Verification code expired. Please resend.')
        del request.session['verification_email']
        del request.session['verification_otp']
        del request.session['otp_expiry']
        return redirect('user_register')
    
    if request.method == 'POST':
        submitted_otp = request.POST.get('otp')

        if submitted_otp == stored_otp:
            try:
                user = CustomUser.objects.get(email=verification_email)
                user.is_active = True
                user.save()

                request.session['login_after_verify'] = user.id
                
                del request.session['verification_email']
                del request.session['verification_otp']
                del request.session['otp_expiry']

                return redirect('post_verification_login')

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


def post_verification_login(request):
    user_id = request.session.get('login_after_verify')

    if not user_id:
        return redirect("user_login")

    user = CustomUser.objects.get(id=user_id)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    del request.session['login_after_verify']

    messages.success(request, "Email successfully verified. Welcome!")
    return redirect("apply_referral")


# ================== APPLY REFERRAL ==============
@login_required
def apply_referral(request):
    if request.user.has_used_referral:
        return redirect("user_homepage")
    
    if request.method == "GET":
        if not request.user.has_seen_referral_page:
            request.user.has_seen_referral_page = True
            request.user.save()

    
    if request.method == "POST":
        code = request.POST.get("referral_code","").strip().upper()

        try:
            referral = Referral.objects.get(referral_code = code)
        
            if referral.user_id == request.user.id:
                messages.error(request, "You cannot use your own referral code.")
                return redirect("apply_referral")
            
            if ReferralUsage.objects.filter(receiver=request.user).exists():
                messages.error(request, "Referral already used.")
                return redirect("user_homepage")
            
            with transaction.atomic():
                from wallet.models import Wallet, WalletTransaction
                reward = ReferralReward.objects.filter(is_active=True).first()
                referrer_amount= reward.referrer_amount if reward else 0
                receiver_amount = reward.receiver_amount if reward else 0

                ReferralUsage.objects.create(
                    referrer=referral.user,
                    receiver=request.user,
                    referrer_reward_amount=referrer_amount,
                    receiver_reward_amount=receiver_amount
                )
                referrer_wallet, _ = Wallet.objects.get_or_create(user=referral.user)
                referrer_wallet.balance = F('balance') + referrer_amount
                referrer_wallet.save(update_fields=['balance'])

                WalletTransaction.objects.create(
                    wallet=referrer_wallet,
                    amount=referrer_amount,
                    transaction_type="REFERRAL",
                    description=f"Referral reward for referring {request.user.email}"
                )

                receiver_wallet, _ = Wallet.objects.get_or_create(user=request.user)
                receiver_wallet.balance = F('balance') + receiver_amount
                receiver_wallet.save(update_fields=['balance'])

                WalletTransaction.objects.create(
                    wallet=receiver_wallet,
                    amount=receiver_amount,
                    transaction_type="REFERRAL",
                    description=f"Referral bonus for using code {referral.referral_code}"
                )

                referral.used_count += 1
                referral.save()

                request.user.has_used_referral = True
                request.user.save()

            messages.success(request, "Referral applied successfully!")
            return redirect("user_homepage")
        
        except Referral.DoesNotExist:
            messages.error(request, "Invalid referral code.")
            return redirect("apply_referral")

    reward = ReferralReward.objects.filter(is_active=True).first()
    context = {
        'reward_amount': reward.receiver_amount if reward else 0
    }
            
    return render(request, "accounts/user_apply_referral.html", context)

# ================== USER RESEND OTP VERIFICATION  ==============
@never_cache
@require_POST
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
                reset_otp = random.randint(100000, 999999)
                request.session['reset_email'] = email
                request.session['reset_otp'] = str(reset_otp)
                request.session['otp_expiry'] = (timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).timestamp()
                
                email_sent = send_otp_email(email, reset_otp, subject_prefix="Password Reset")

                if email_sent:
                    messages.success(request, 'A password reset code has been sent to your email.')
                else:
                    messages.error(request, 'If an account exists, a reset code has been sent, but there was an email error.')

                return redirect('user_reset_password_verify')

            except CustomUser.DoesNotExist:
                messages.error(request, 'If an account exists, a reset code has been sent.')
                return redirect('user_forgot_password') 
    else:
        form = UserForgotPasswordForm()
    
    return render(request, 'accounts/user_forgot_password.html', {'form': form})


# ======================= PASSWORD RESET VERIFICATION  =====================
@never_cache
def user_reset_password_verify(request):
    reset_email = request.session.get('reset_email')
    stored_otp = request.session.get('reset_otp')
    otp_expiry = request.session.get('otp_expiry')

    if not reset_email:
        messages.error(request, 'Password reset session invalid.')
        return redirect('user_forgot_password') 

    if timezone.now().timestamp() > float(otp_expiry):
        messages.error(request, 'Reset code expired. Please try again.')
        del request.session['reset_email']
        del request.session['reset_otp']
        del request.session['otp_expiry']
        return redirect('user_forgot_password')

    if request.method == 'POST':
        submitted_otp = request.POST.get('otp') 

        if submitted_otp == stored_otp:
            request.session['otp_verified'] = True 
            
            del request.session['reset_otp']
            del request.session['otp_expiry']
            
            messages.success(request, 'Verification successful. You can now set a new password.')
            return redirect('user_reset_password') 
        else:
            messages.error(request, 'Invalid verification code.')
    
    context = {
        'reset_email': reset_email,
        'otp_expiry': otp_expiry,
    }
    return render(request, 'accounts/user_otp_verify.html', context) 

# ===================== PASSWORD RESET FINAL STEP ==================
@never_cache
def user_reset_password(request):
    reset_email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')

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
            
            user.set_password(new_password)
            user.save()

            del request.session['reset_email']
            del request.session['otp_verified']
            
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
    return redirect('user_login')

# to prevent Google OAuth from running again if the user is already authenticated.
# def google_callback(request, *args, **kwargs):
#     if request.user.is_authenticated:
#         return redirect("user_homepage")
    
#     return oauth2_callback(request, *args, **kwargs)






