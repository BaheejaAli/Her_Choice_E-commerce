from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "frontend_pages/user/homepage.html")

def admin_dashboard(request):
    return render(request, "frontend_pages/admin/dashboard.html")
