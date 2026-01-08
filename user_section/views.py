from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from products.models import Product
from brandsandcategories.models import Category
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .forms import UserProfileUpdateForm, UserAddressForm

# Create your views here.
class HomePageView(TemplateView):
    template_name = "user_section/homepage.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["new_arrivals"] = Product.objects.filter(is_active = True).order_by("-created_at")[:8]
        context["featured_products"] = Product.objects.filter(is_active=True, is_featured=True).order_by('?')[:6]
        context["categories"] = Category.objects.filter(is_active=True).order_by('?')[:4]
        context["trending_products"] = Product.objects.filter(is_most_demanded=True,is_active=True).order_by('?')[:8]

        return context

class AboutPageView(TemplateView):
    template_name = "user_section/about.html"


@login_required
def profile_info(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default')
    context = {
        'user':user,
        'addresses':addresses
    }
    return render(request, "user_section/profile.html",context)

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
    address = user.addresses.all().order_by('-is_default')
    return render(request, "user_section/profile_address.html",{'user':user,'address':address})           

@login_required
def profile_add_address(request):
    if request.method =="POST":
        form = UserAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('profile_address')
        
    else:
        form = UserAddressForm()  
    return render(request, "user_section/profile_add_address.html",{'form':form})


   
    



