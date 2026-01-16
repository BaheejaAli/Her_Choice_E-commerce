from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from products.models import Product, ProductVariantImage
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
from datetime import timedelta
from django.utils import timezone
from accounts.models import CustomUser

# Create your views here.
def attach_display_image(products):
    for product in products:
        product.display_image = None

        primary = ProductVariantImage.objects.filter(
            variant__product=product,
            variant__is_active=True,
            is_primary=True
        ).first()

        if primary:
            product.display_image = primary.image
            print("IMAGE FOUND →", product.name, product.display_image)
        else:
            print("NO IMAGE →", product.name)

def homepage(request):
    new_arrivals = (
        Product.objects
        .filter(is_active=True)
        .prefetch_related("variants__images")
        .order_by("-created_at")[:8]
    )

    featured_products = (
        Product.objects
        .filter(is_active=True, is_featured=True)
        .prefetch_related("variants__images")
        .order_by("?")[:6]
    )

    trending_products = (
        Product.objects
        .filter(is_active=True, is_most_demanded=True)
        .prefetch_related("variants__images")
        .order_by("?")[:8]
    )

    # 🔑 CALL THE FUNCTION HERE
    attach_display_image(new_arrivals)
    attach_display_image(featured_products)
    attach_display_image(trending_products)

    categories = Category.objects.filter(is_active=True).order_by("?")[:4]

    return render(
        request,
        "user_section/homepage.html",
        {
            "new_arrivals": new_arrivals,
            "featured_products": featured_products,
            "trending_products": trending_products,
            "categories": categories,
        }
    )

   
class AboutPageView(TemplateView):
    template_name = "user_section/about.html"


@login_required
def profile_info(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default')
    context = {
        'user': user,
        'addresses': addresses
    }
    return render(request, "user_section/profile.html", context)


@login_required
def upload_profile_pic(request):
    if request.method == "POST":
        if "profile_image" in request.FILES:
            user = request.user
            user.profile_pic = request.FILES["profile_image"]
            user.save()
            return JsonResponse({"status": "success", "image_url": user.profile_pic.url})
    return JsonResponse({"status": "error"})


@login_required
def edit_profile(request):
    user = request.user
    old_email = user.email
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=request.user)

        if form.is_valid():
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
    if not form.is_valid():
        print("FORM ERRORS:", form.errors)

    # print("FORM VALID:", form.is_valid())
    # print("FORM ERRORS:", form.errors)
    # print("OLD EMAIL:", old_email)
    # print("NEW EMAIL:", form.cleaned_data.get('email') if form.is_valid() else None)

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
    if request.method == "POST":
        form = UserAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if request.POST.get('setDefault') == 'on':
                request.user.addresses.all().update(is_default=False)
                address.is_default = True
            address.save()
            return redirect('profile_address')

    else:
        form = UserAddressForm()
    return render(request, "user_section/profile_add_edit_address.html", {'form': form, 'edit_mode': False})


@login_required
def profile_edit_address(request, address_id):
    address = get_object_or_404(request.user.addresses, id=address_id)

    if request.method == 'POST':
        form = UserAddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            if request.POST.get('setDefault') == 'on':
                request.user.addresses.all().update(is_default=False)
                updated_address.is_default = True
            updated_address.save()
            return redirect('profile_address')
    else:
        form = UserAddressForm(instance=address)

    return render(request, "user_section/profile_add_edit_address.html", {'form': form, 'edit_mode': True})


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
