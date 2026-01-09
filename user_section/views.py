from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from products.models import Product
from brandsandcategories.models import Category
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .forms import UserProfileUpdateForm, UserAddressForm
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

# Create your views here.


class HomePageView(TemplateView):
    template_name = "user_section/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["new_arrivals"] = Product.objects.filter(
            is_active=True).order_by("-created_at")[:8]
        context["featured_products"] = Product.objects.filter(
            is_active=True, is_featured=True).order_by('?')[:6]
        context["categories"] = Category.objects.filter(
            is_active=True).order_by('?')[:4]
        context["trending_products"] = Product.objects.filter(
            is_most_demanded=True, is_active=True).order_by('?')[:8]

        return context


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


# @login_required
# def upload_profile_pic(request):
#     print("REQUEST METHOD:", request.method)
#     print("FILES:", request.FILES)
#     if request.method == 'POST' and request.FILES.get('profile_pic'):
#         user = request.user
#         user.profile_pic = request.FILES['profile_pic']
#         user.save()
#         print("IMAGE SAVED")
#         return JsonResponse({'status':'success',
#                              "image_url": user.profile_pic.url})
#     return JsonResponse({'status':'error'}, status=400)
@login_required
def upload_profile_pic(request):
    print("METHOD:", request.method)
    print("FILES:", request.FILES)

    if request.method == "POST":
        if "profile_image" in request.FILES:
            print("IMAGE RECEIVED ✅")
            user = request.user
            user.profile_pic = request.FILES["profile_image"]
            user.save()
            print("IMAGE SAVED ✅")
            return JsonResponse({"status": "success"})
        else:
            print("NO IMAGE ❌")

    return JsonResponse({"status": "error"})

#     print("REQUEST METHOD:", request.method)
#     print("FILES:", request.FILES)

#     if request.method == 'POST' and request.FILES.get('profile_image'):
#         user = request.user
#         user.profile_pic = request.FILES['profile_image']
#         user.save()

#         return JsonResponse({
#             'status': 'success',
#             'image_url': user.profile_pic.url
#         })

#     return JsonResponse({'status': 'error'}, status=400)



@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile_info') 
    else:
        form = UserProfileUpdateForm(instance=request.user)
    
    return render(request, 'user_section/profile_edit.html', {'form': form})

@login_required
def profile_address(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default')
    return render(request, "user_section/profile_address.html",{'user':user,'addresses':addresses})           

@login_required
def profile_add_address(request):
    if request.method =="POST":
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
    return render(request, "user_section/profile_add_edit_address.html",{'form':form,'edit_mode':False})

@login_required
def profile_edit_address(request, address_id):
    address = get_object_or_404(request.user.addresses, id=address_id)

    if request.method == 'POST':
        form = UserAddressForm(request.POST,instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            if request.POST.get('setDefault') == 'on':
                request.user.addresses.all().update(is_default=False)
                updated_address.is_default = True
            updated_address.save()
            return redirect('profile_address')
    else:
        form = UserAddressForm(instance=address)

    
    return render(request, "user_section/profile_add_edit_address.html",{'form':form,'edit_mode':True})

@login_required
def profile_delete_address(request,address_id):
    address = get_object_or_404(request.user.addresses, id=address_id)

    if request.method == "POST":
        address.delete()
    return redirect('profile_address')

   
    



