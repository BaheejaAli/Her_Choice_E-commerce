from django.shortcuts import render, redirect, get_object_or_404
from offer.models import Offer
from offer.forms import OfferForm
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from brandsandcategories.models import Category

def offer_management(request):
    offer_type = request.GET.get('type')
    offers = Offer.objects.prefetch_related('product','category')
    if offer_type in ['product','category']:
        offers = offers.filter(offer_type=offer_type)
    
    offer_list = []
    for offer in offers:
        if offer.offer_type=='product':
            targets = "<br>".join(p.name for p in offer.product.all())
        elif offer.offer_type=='category':
            targets = "<br>".join(c.name for c in offer.category.all())
        else:
            targets = 'No Targets'
        offer_list.append({
            'offer': offer,
            'targets': targets
        })

    context = {
        'offer_list': offer_list,
        'all_offers_count': Offer.objects.count(),
        'product_offers_count': Offer.objects.filter(offer_type='product').count(),
        'category_offers_count': Offer.objects.filter(offer_type='category').count(),
    }
    return render(request, "admin_panel/offer_list.html", context)

def offer_create(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()
            form.save_m2m()
            messages.success(request, "Offer created successfully!")
            return redirect('offer_management')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OfferForm()
    
    return render(request, "admin_panel/offer_create.html",{'form':form, 'is_edit':False})

def search_products(request):
    search_value = request.GET.get('q', '')
    
    if len(search_value) >= 2:
        products = Product.objects.filter(name__icontains=search_value)[:10]
        results = [{"id": p.id, "text": p.name} for p in products]
    else:
        results = []
        
    return JsonResponse({'results': results})

def search_category(request):
    search_value = request.GET.get('q', '')
    
    if len(search_value) >= 2:
        categories = Category.objects.filter(name__icontains=search_value)[:10]
        results = [{"id": c.id, "text": c.name} for c in categories]
    else:
        results = []
        
    return JsonResponse({'results': results})

def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)

    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()
            form.save_m2m()
            messages.success(request, "Offer updated successfully!")
            return redirect('offer_management')
        else:
            messages.error(request, "There was an error updating the offer.")
    else:
        form = OfferForm(instance=offer)
    return render(request, "admin_panel/offer_create.html", {
        'form': form, 
        'is_edit': True, 
        'offer': offer,
        'selected_products':list(offer.product.values('id','name')),
        'selected_categories':list(offer.category.values('id','name'))
    })

def toggle_offer_status(request, offer_id):
    offer = get_object_or_404(Offer, id= offer_id)
    offer.is_active = not offer.is_active
    offer.save()
    return JsonResponse({'status': 'success', 'is_active': offer.is_active})

def delete_offer(request, offer_id):
    offer = get_object_or_404(Offer, id= offer_id)
    if request.method == 'POST':
        offer.delete()
        return JsonResponse({
            'status':'success',
            'message':'Offer deleted successfully!'
        })

    

