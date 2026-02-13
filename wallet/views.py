from django.shortcuts import render,redirect
from .models import Wallet, WalletTransaction
from offer.models import ReferralReward, Referral
from django.contrib import messages
from django.db import transaction

# Create your views here.
def wallet_dashboard(request):
    wallet,_ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()
    active_reward = ReferralReward.objects.filter(is_active=True).first()
    user_referral,_ = Referral.objects.get_or_create(user=request.user)


    context = {
        "wallet":wallet,
        "transactions":transactions,
        "active_reward": active_reward,
        "user_referral": user_referral,
    }
    return render(request, "wallet/wallet_dashboard.html", context)

def add_money(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        
        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect('wallet_dashboard')
            
            with transaction.atomic():
                wallet,created = Wallet.objects.get_or_create(user= request.user)
                wallet.add_funds(amount)

                WalletTransaction.objects.create(wallet=wallet, amount=amount, transaction_type='DEPOSIT')
                messages.success(request, f"Successfully added ₹ {amount} to your wallet.")
            return redirect('wallet_dashboard')
            
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")
            
    return render(request, 'wallet/add_money.html')

    
