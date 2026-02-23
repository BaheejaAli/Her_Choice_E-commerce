from django.shortcuts import render, redirect, get_object_or_404
from offer.models import Offer
from offer.forms import OfferForm
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from brandsandcategories.models import Category
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
@never_cache
def offer_management(request):
    offer_type = request.GET.get('type','all')
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

    paginator = Paginator(offer_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "offer_list": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "page_range": paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        ),
        
        'all_offers_count': Offer.objects.count(),
        'product_offers_count': Offer.objects.filter(offer_type='product').count(),
        'category_offers_count': Offer.objects.filter(offer_type='category').count(),
    }
    return render(request, "admin_panel/offer_list.html", context)

@login_required
@user_passes_test(is_admin)
@never_cache
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

@login_required
@user_passes_test(is_admin)
def search_products(request):
    search_value = request.GET.get('q', '')
    
    if len(search_value) >= 2:
        products = Product.objects.filter(name__icontains=search_value)[:10]
        results = [{"id": p.id, "text": p.name} for p in products]
    else:
        results = []
        
    return JsonResponse({'results': results})

@login_required
@user_passes_test(is_admin)
def search_category(request):
    search_value = request.GET.get('q', '')
    
    if len(search_value) >= 2:
        categories = Category.objects.filter(name__icontains=search_value)[:10]
        results = [{"id": c.id, "text": c.name} for c in categories]
    else:
        results = []
        
    return JsonResponse({'results': results})

@login_required
@user_passes_test(is_admin)
@never_cache
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

@require_POST
@login_required
@user_passes_test(is_admin)
def toggle_offer_status(request, offer_id):
    offer = get_object_or_404(Offer, id= offer_id)
    offer.is_active = not offer.is_active
    offer.save()
    return JsonResponse({'status': 'success', 'is_active': offer.is_active})

@require_POST
@login_required
@user_passes_test(is_admin)
def delete_offer(request, offer_id):
    offer = get_object_or_404(Offer, id= offer_id)
    if request.method == 'POST':
        offer.delete()
        return JsonResponse({
            'status':'success',
            'message':'Offer deleted successfully!'
        })

    

