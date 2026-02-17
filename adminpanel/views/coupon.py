from offer.models import Coupon
from offer.forms import CouponForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse

def coupon_management(request):
    coupons = Coupon.objects.all().order_by('-created_at')

    query = request.GET.get("q","").strip()
    if query:
        coupons = coupons.filter(Q(code__icontains=query))

    status = request.GET.get("status","").strip()
    now = timezone.now()

    if status == "active":
        coupons = coupons.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        )
    elif status == "inactive":
        coupons = coupons.filter(is_active=False)

    elif status == "expired":
        coupons = coupons.filter(valid_to__lt=now)

    elif status == "scheduled":
        coupons = coupons.filter(valid_from__gt=now)

    total_coupons = Coupon.objects.count()
    active_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now(),).count()

    expired_coupons = Coupon.objects.filter(valid_to__lt=now).count()


    context = {
        "coupons": coupons,
        "status" :status,
        "total_coupons": total_coupons,
        "active_coupons": active_coupons,
        "search_query": query
    }
    return render(request, "admin_panel/coupon_management.html", context)

def create_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully!")
            return redirect('coupon_management')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm()

    return render(request, "admin_panel/coupon_form.html", {"form": form})


def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully!")
            return redirect('coupon_management')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm(instance=coupon)

    return render(request, "admin_panel/coupon_form.html", {"form": form})

def toggle_coupon_status(request, coupon_id):
    if request.method == 'POST':
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=['is_active'])
    return JsonResponse({
        'success': True,
        'is_active': coupon.is_active,
        'message': (
            "Coupon activated."
            if coupon.is_active
            else "Coupon deactivated."
        )
    })


def delete_coupon(request, coupon_id):
    if request.method == 'POST':
        print("the delete")
        coupon = get_object_or_404(Coupon, id=coupon_id)
        code = coupon.code
        coupon.delete()
        print(code)
        
        messages.success(request, f'Coupon "{code}" has been deleted.')
    
    return redirect('coupon_management')



