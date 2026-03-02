from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from orders.models import Order,OrderItem
from products.models import ProductVariant
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.db.models.functions import TruncMonth, TruncDay, TruncHour
from django.utils import timezone
from datetime import timedelta


# ######### ADMIN CHECK #############
def is_admin(user):
    return user.is_staff or user.is_superuser

def get_dashboard_totals(filtered_orders):

    total_revenue = filtered_orders.aggregate(total=Sum('total'))['total'] or 0
    total_orders = filtered_orders.count()
    total_stock = ProductVariant.objects.aggregate(total=Sum('stock'))['total'] or 0

    User = get_user_model()
    total_customers = User.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()

    return total_revenue, total_orders, total_customers, total_stock

def get_sales_chart_data(filtered_orders, date_range):
    now = timezone.now()

    if date_range == "today":
        filtered_orders = filtered_orders.filter(created_at__date=now.date())
        sales_data = (
            filtered_orders
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(total=Sum('total'))
            .order_by('hour')
        )
        labels = [item["hour"].strftime("%I %p") for item in sales_data]
        data = [float(item['total'] or 0) for item in sales_data]

    elif date_range == "week":
        week_ago = now - timedelta(days=7)
        filtered_orders = filtered_orders.filter(created_at__gte=week_ago)
        sales_data = (
            filtered_orders
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('total'))
            .order_by('day')
        )
        labels = [item['day'].strftime("%d %b") for item in sales_data]
        data = [float(item['total'] or 0) for item in sales_data]

    elif date_range == "month":
        filtered_orders = filtered_orders.filter(created_at__year=now.year, created_at__month=now.month)
        sales_data = (
            filtered_orders
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('total'))
            .order_by('day')
        )
        labels = [item['day'].strftime("%d %b") for item in sales_data]
        data = [float(item['total'] or 0) for item in sales_data]

    elif date_range == "year":
        filtered_orders = filtered_orders.filter(created_at__year=now.year)
        sales_data = (
            filtered_orders
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('total'))
            .order_by('month')
        )
        labels = [item['month'].strftime("%b") for item in sales_data]
        data = [float(item['total'] or 0) for item in sales_data]

    return labels, data

def get_top_products():
    top_products = (
        OrderItem.objects
        .filter(order__status__in=['delivered'])
        .values('variant__product__name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:10]
    )
    return top_products

def get_top_categories():
    top_categories = (
        OrderItem.objects
        .filter(order__status__in=['delivered'])
        .values('variant__product__category__name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:10]
    )
    return top_categories

def get_top_brands():
    top_brands = (
        OrderItem.objects
        .filter(order__status__in=['delivered'])
        .values('variant__product__brand__name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:10]
    )
    return top_brands


@never_cache
@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def admin_dashboard(request):

    date_range = request.GET.get("date_range", "today")
    filtered_orders = Order.objects.exclude(status__in=['cancelled','failed'])

    total_revenue, total_orders, total_customers, total_stock = get_dashboard_totals(filtered_orders)

    labels, data = get_sales_chart_data(filtered_orders, date_range)
    top_products = get_top_products()
    top_categories = get_top_categories()
    top_brands = get_top_brands()

    recent_orders = Order.objects.order_by('-created_at')[:5]

    context = {
        "total_revenue":total_revenue,
        "total_orders":total_orders,
        "total_customers":total_customers,
        "total_stock":total_stock,
        "chart_labels": labels,
        "chart_data": data,
        "date_range":date_range,
        "top_products":top_products,
        "top_categories":top_categories,
        "top_brands":top_brands,
        "recent_orders":recent_orders
    }
    return render(request, "admin_panel/dashboard.html", context)


