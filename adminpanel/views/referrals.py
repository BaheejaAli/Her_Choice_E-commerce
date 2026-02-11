from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from offer.models import ReferralReward
from django.http import JsonResponse
from django.views.decorators.http import require_POST

def referral_reward_list(request):
    rewards = ReferralReward.objects.all()

    return render(request, "admin_panel/referral_reward_list.html", {
        "rewards": rewards   
    })

def referral_reward_add(request):
    if request.method == "POST":
        referrer_amount = request.POST.get("referrer_amount")
        receiver_amount = request.POST.get("receiver_amount")
        is_active = True if request.POST.get("is_active") else False

        ReferralReward.objects.create(
            referrer_amount=Decimal(referrer_amount),
            receiver_amount=Decimal(receiver_amount),
            is_active=is_active
        )
        messages.success(request, "Referral reward created successfully.")
        return redirect("referral_reward_list")

    return render(request, "admin_panel/referral_reward_form.html")

def referral_reward_edit(request, id):
    reward = get_object_or_404(ReferralReward, id=id)

    if request.method == "POST":
        reward.referrer_amount = Decimal(request.POST.get("referrer_amount"))
        reward.receiver_amount = Decimal(request.POST.get("receiver_amount"))
        reward.is_active = True if request.POST.get("is_active") else False
        reward.save()

        messages.success(request, "Referral reward updated successfully.")
        return redirect("referral_reward_list")

    return render(request, "admin_panel/referral_reward_form.html", {
        "reward": reward
    })

@require_POST
def referral_reward_toggle(request, id):
    reward = get_object_or_404(ReferralReward, id=id)
    reward.is_active = not reward.is_active
    reward.save(update_fields=['is_active'])

    return JsonResponse({
        'success': True,
        'is_active': reward.is_active,
        'message': (
            f'Referral reward activated.'
            if reward.is_active
            else f'Referral reward deactivated.'
        )
    })
