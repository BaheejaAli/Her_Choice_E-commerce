from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from orders.models import Order
from products.models import ProductVariant
from django.db.models import Sum
from django.contrib.auth import get_user_model


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

@never_cache
@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def admin_dashboard(request):

    User = get_user_model()

    filter_type = request.GET.get("filter_type","monthly")

    orders = Order.objects.exclude(status__in=['cancelled','failed'])
    total_revenue = orders.aggregate(total=Sum('total'))['total'] or 0  
    total_orders = orders.count()
    total_customers = User.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()
    total_stock = ProductVariant.objects.aggregate(total = Sum('stock'))['total'] or 0

    context = {
        "total_revenue":total_revenue,
        "total_orders":total_orders,
        "total_customers":total_customers,
        "total_stock":total_stock
    }
    return render(request, "admin_panel/dashboard.html", context)

