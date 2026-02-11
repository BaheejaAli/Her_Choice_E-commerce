from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Referral, ReferralUsage
from django.contrib import messages
from django.db import transaction

# Create your views here.

@login_required
def apply_referral_page(request):
    if request.user.has_used_referral:
        return redirect("user_homepage")
    
    if request.method == "GET":
        if not request.user.has_seen_referral_page:
            request.user.has_seen_referral_page = True
            request.user.save()

    
    if request.method == "POST":
        code = request.POST.get("referral_code")

        try:
            referral = Referral.objects.get(referral_code = code)
        except Referral.DoesNotExist:
            messages.error(request, "Invalid referral code.")
            return redirect("apply_referral")
        
        if referral.user == request.user:
            messages.error(request, "You cannot use your own referral code.")
            return redirect("apply_referral")
        
        if ReferralUsage.objects.filter(receiver=request.user).exists():
            messages.error(request, "Referral already used.")
            return redirect("user_homepage")
        
        with transaction.atomic():
            ReferralUsage.objects.create(
                referrer=referral.user,
                receiver=request.user,
                referrer_reward_points=100,
                receiver_reward_points=50
            )

            referral.used_count += 1
            referral.save()

            request.user.has_used_referral = True
            request.user.save()

            messages.success(request, "Referral applied successfully!")
            return redirect("user_homepage")





    return render(request, "offer/apply_referral.html")

    

