from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from products.models import Product, ProductVariant
from accounts.forms import ProfilePicForm
from brandsandcategories.models import Category
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .forms import UserProfileUpdateForm, UserAddressForm
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
import random
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from datetime import timedelta
from django.utils import timezone
from accounts.models import CustomUser
from .models import Wishlist, WishlistItem
from django.db import transaction
from .models import UserAddress
from products.utils import prepare_products_for_display
from offer.models import Referral 
from wallet.models import Wallet


def homepage(request):
    # Get IDs of products that have at least one active variant
    # This prevents duplicates and ensures we only show available items
    active_product_ids = ProductVariant.objects.filter(is_active=True).values_list('product_id', flat=True)

    new_arrivals = (
        Product.objects
        .filter(is_active=True, id__in=active_product_ids)
        .prefetch_related("variants__images")
        .order_by("-created_at")[:16]
    )

    featured_products = (
        Product.objects
        .filter(is_active=True, is_featured=True, id__in=active_product_ids)
        .prefetch_related("variants__images")
        .order_by("?")[:8]
    )

    trending_products = (
        Product.objects
        .filter(is_active=True, is_most_demanded=True, id__in=active_product_ids)
        .prefetch_related("variants__images")
        .order_by("?")[:8]
    )
    prepare_products_for_display(new_arrivals)
    prepare_products_for_display(featured_products)
    prepare_products_for_display(trending_products)

    return render(
        request,
        "user_section/homepage.html",
        {
            "new_arrivals": new_arrivals,
            "featured_products": featured_products,
            "trending_products": trending_products,
        }
    )
   
class AboutPageView(TemplateView):
    template_name = "user_section/about.html"

class ContactPageView(TemplateView):
    template_name = "user_section/contact.html"


@login_required
def profile_info(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default')
    referral, _ = Referral.objects.get_or_create(user=user)
    wallet, _ = Wallet.objects.get_or_create(user=user)
    context = {
        'user': user,
        'addresses': addresses,
        'referral': referral,
        'wallet': wallet,
    }
    return render(request, "user_section/profile.html", context)


@login_required
def upload_profile_pic(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Invalid request method"
        }, status=405)
   
    form=ProfilePicForm(request.POST, request.FILES, instance=request.user )
    if form.is_valid():
        form.save()
        return JsonResponse({
            "status": "success",
            "message": "Profile picture updated successfully!"
        }, status=200)

    return JsonResponse({
        "status": "error",
        "message": form.errors.get('profile_pic', ['Invalid image'])[0]
    }, status=400)



@login_required
def edit_profile(request):
    user = request.user
    old_email = user.email
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=request.user)

        if form.is_valid():
            print("the form is valid")
            new_email = form.cleaned_data['email']

            # EMAIL CHANGED
            if new_email != old_email:
                if CustomUser.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                    messages.error(
                        request, 'This email is already taken by another user.')
                    return redirect('profile_info')
               # check OTP already sent, don't generate again
                existing_otp = request.session.get('profile_otp')
                existing_expiry = request.session.get('profile_otp_expiry')

                if existing_otp and existing_expiry:
                    messages.info(request, 'OTP already sent. Please verify.')
                    return redirect('profile_otp_verify')

                otp = str(random.randint(100000, 999999))

                # Save other fields EXCEPT email
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.gender = form.cleaned_data['gender']
                user.phone = form.cleaned_data['phone']
                user.save()

                # store OTP in session
                request.session['profile_otp'] = otp
                request.session['profile_email'] = new_email
                request.session['profile_otp_expiry'] = (
                    timezone.now() + timedelta(minutes=2)
                ).timestamp()

                try:
                    send_mail(
                        subject='Verify your email',
                        message=f'Your OTP is {otp}',
                        from_email=None,
                        recipient_list=[new_email],
                        fail_silently=False,
                    )
                except Exception:
                    messages.error(request, "Email could not be sent.")

                print("otp:", otp)
                print("new_email:", new_email)
                messages.info(request, 'OTP sent to your new email')
                return redirect('profile_otp_verify')

            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('profile_info')
    else:

        form = UserProfileUpdateForm(instance=request.user)
    return render(request, 'user_section/profile_edit.html', {'form': form})


@login_required
def profile_otp_verify(request):
    otp = request.session.get('profile_otp')
    email = request.session.get('profile_email')
    otp_expiry = request.session.get('profile_otp_expiry')

    if not email:
        messages.error(request, 'Verification session expired.')
        return redirect('profile_info')

    if not otp_expiry or timezone.now().timestamp() > float(otp_expiry):
        messages.error(request, 'OTP expired. Please resend.')

        # clean session
        request.session.pop('profile_otp', None)
        # request.session.pop('profile_email', None)
        request.session.pop('profile_otp_expiry', None)

        return redirect('profile_otp_verify')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        if otp == entered_otp:
            user = request.user
            user.email = email
            user.save()

            request.session.pop('profile_otp', None)
            request.session.pop('profile_email', None)
            request.session.pop('profile_otp_expiry', None)

            messages.success(request, 'Email updated successfully')
            return redirect('profile_info')
        else:
            messages.error(request, 'Invalid OTP')
    return render(request, 'user_section/profile_otp_verify.html', {'otp_expiry': otp_expiry})


@login_required
def profile_resend_otp(request):
    email = request.session.get('profile_email')

    if not email:
        messages.error(request, 'Verification session expired.')
        return redirect('profile_info')

    otp = str(random.randint(100000, 999999))

    request.session['profile_otp'] = otp
    request.session['profile_otp_expiry'] = (
        timezone.now() + timedelta(minutes=2)
    ).timestamp()

    send_mail(
        subject='Verify your email',
        message=f'Your OTP is {otp}',
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )

    messages.success(request, 'A new OTP has been sent.')
    return redirect('profile_otp_verify')


@login_required
def profile_address(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default')
    return render(request, "user_section/profile_address.html", {'user': user, 'addresses': addresses})


@login_required
def profile_add_address(request):

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = UserAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if request.POST.get('setDefault') == 'on':
                request.user.addresses.all().update(is_default=False)
                address.is_default = True
            address.save()
            if next_url:
                return redirect(next_url)
            return redirect('profile_address')

    else:
        form = UserAddressForm()
    return render(request, "user_section/profile_add_edit_address.html", {'form': form, 'edit_mode': False, 'next': next_url})


@login_required
def profile_edit_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == 'POST':
        form = UserAddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            if request.POST.get('setDefault') == 'on':
                request.user.addresses.all().update(is_default=False)
                updated_address.is_default = True
            updated_address.save()
            if next_url:
                return redirect(next_url)
            return redirect('profile_address')
    else:
        form = UserAddressForm(instance=address)

    return render(request, "user_section/profile_add_edit_address.html", {'form': form, 'edit_mode': True, 'next': next_url})


@login_required
def profile_delete_address(request, address_id):
    address = get_object_or_404(request.user.addresses, id=address_id)

    if request.method == "POST":
        address.delete()
    return redirect('profile_address')


@login_required
def profile_change_password(request):
    if request.method == "POST":
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        # Check old password
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect')
            return render(request, 'user_section/profile_change_password.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return render(request, 'user_section/profile_change_password.html')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters')
            return render(request, 'user_section/profile_change_password.html')

        user.set_password(new_password)
        user.save()

        # Keep user logged in
        update_session_auth_hash(request, user)
        messages.success(request, 'Password updated successfully')
        return redirect('profile_info')
    return render(request, "user_section/profile_change_password.html")

@login_required
def wishlist_view(request):
    wishlist, created = Wishlist.objects.get_or_create(user = request.user)
    wishlist_items = wishlist.items.select_related(
        "variant",
        "variant__product",
        "variant__color",
        "variant__size"
    )
    
    for item in wishlist_items:
        pricing = item.variant.get_pricing_data()
        item.variant.final_price = pricing["final_price"]
        item.variant.discount_percentage = pricing["discount_percentage"]
        item.variant.active_offer = pricing["active_offer"]

    context = {
        "wishlist": wishlist,
        "wishlist_items": wishlist_items,
    }
    return render(request,"user_section/wishlist.html",context)

@login_required
@require_POST
def add_to_wishlist(request):
    variant_id = request.POST.get("variant_id")
    if not variant_id:
        return JsonResponse({
            "status" : "error",
            "message" : "Variant ID is required"
        },status=400)
    variant = get_object_or_404(
        ProductVariant,
        id = variant_id,
        is_active = True,
        product__is_active = True,
        product__category__is_active = True,
        product__brand__is_active = True
    )

    with transaction.atomic():
        wishlist, _ = Wishlist.objects.get_or_create(user = request.user)
        wishlist_item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, variant=variant)

    if not created:
        return JsonResponse({
             "status" : "error",
            "message" : "Already in wishlist"
        },status=400)
    
    return JsonResponse({
        "status": "success",
        "message": "Added to wishlist"
    })
        
@login_required
@require_POST
def remove_from_wishlist(request):
    item_id = request.POST.get("item_id")
    wishlist = get_object_or_404(Wishlist, user=request.user)
    item = get_object_or_404(WishlistItem, id = item_id, wishlist=wishlist)
    item.delete()
    return JsonResponse({
        "status":"success",
        "message":"Removed from wishlist"
    })



