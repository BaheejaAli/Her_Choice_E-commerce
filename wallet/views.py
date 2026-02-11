from django.shortcuts import render
from .models import Wallet

# Create your views here.
def wallet_dashboard(request):
    wallet,_ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()

    context = {
        "wallet":wallet,
        "transactions":transactions,
    }
    return render(request, "wallet/wallet_dashboard.html", context)
