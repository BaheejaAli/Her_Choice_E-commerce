from django.shortcuts import render
from offer.models import Offer

def offer_management(request):
    offers = Offer.objects.all()
    return render(request, "admin_panel/offer_list.html",{'offers':offers})

def offer_create(request):
    
    return render(request, "admin_panel/offer_create.html")