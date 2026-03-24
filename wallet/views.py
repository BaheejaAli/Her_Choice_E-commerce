from django.shortcuts import render,redirect
from .models import Wallet, WalletTransaction
from offer.models import ReferralReward, Referral
from django.contrib import messages
from django.db import transaction
import razorpay
from django.conf import settings
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

# Create your views here.
@login_required
def wallet_dashboard(request):
    wallet,_ = Wallet.objects.get_or_create(user=request.user)
    transactions_list = wallet.transactions.all()
    
    # Pagination
    paginator = Paginator(transactions_list, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number)
    
    active_reward = ReferralReward.objects.filter(is_active=True).first()
    user_referral,_ = Referral.objects.get_or_create(user=request.user)

    context = {
        "wallet":wallet,
        "transactions":page_obj.object_list,
        "page_obj":page_obj,
        "page_range":page_range,
        "is_paginated":page_obj.has_other_pages(),
        "active_reward": active_reward,
        "user_referral": user_referral,
    }
    return render(request, "wallet/wallet_dashboard.html", context)

# Initialize Razorpay Client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def add_money(request):
    if request.method == "POST":
        amount = request.POST.get("amount",0)

        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect('wallet_dashboard')
            
            razorpay_order = razorpay_client.order.create({
            "amount": int(amount * 100),  # Amount in paise
            "currency": "INR",
            "payment_capture": "1"
            })

            context = {
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_merchant_key": settings.RAZORPAY_KEY_ID,
                "razorpay_amount": razorpay_order['amount'],
                "amount": amount,
            }
            return render(request, 'wallet/razorpay.html', context)
        
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")
            return redirect('wallet_dashboard')
            
    return render(request, 'wallet/add_money.html')


@login_required
@require_POST
def verify_payment(request):
    if request.method == "POST":
        params_dict = {
            'razorpay_order_id': request.POST.get('razorpay_order_id'),
            'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
            'razorpay_signature': request.POST.get('razorpay_signature')
        }

        try:
            # Verify the signature to ensure payment is real
            razorpay_client.utility.verify_payment_signature(params_dict)

            # Fetch amount from Razorpay
            payment = razorpay_client.payment.fetch(params_dict['razorpay_payment_id'])
            amount = Decimal(str(float(payment['amount']) / 100))

            with transaction.atomic():
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.add_funds(amount)
                
                WalletTransaction.objects.create(
                    wallet=wallet, 
                    amount=amount, 
                    transaction_type='DEPOSIT',
                    description=f"Razorpay Deposit (ID: {params_dict['razorpay_payment_id']})"
                )
            
            messages.success(request, f"₹ {amount} added to your wallet successfully!")
        # except Exception:
        #     messages.error(request, "Payment verification failed.")
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed: Signature mismatch.")
        except Exception as e:
            messages.error(request, "An unexpected error occurred.")
            print(f"Error: {e}")

    return redirect('wallet_dashboard')

    
