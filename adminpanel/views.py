from django.shortcuts import render
from django.views.decorators.cache import never_cache 

# Create your views here.


@never_cache
def user_management(request):
    return render(request, "admin_panel/user_management.html")