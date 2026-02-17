from django.shortcuts import render
from django.db.models import Count, Sum
from orders.models import Order
from django.utils import timezone
from datetime import timedelta
# import openpyxl
from django.http import HttpResponse

def get_filtered_orders(request):
    date_range = request.GET.get('date_range','this_month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    orders = Order.objects.exclude(status__in=['cancelled','failed'])

    today = timezone.now().date()
    start_date = None
    end_date = None
    if date_range == 'daily':
        orders = orders.filter(created_at__date=today)
    elif date_range == 'weekly':
        orders = orders.filter(created_at__date__gte=today - timedelta(days=7))
    elif date_range == 'yearly':
        orders = orders.filter(created_at__year=today.year)
    elif start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    return orders, start_date, end_date

def sales_report(request):
    orders, start_date, end_date = get_filtered_orders(request)
    total = orders.aggregate(
        sales_count = Count('id'),
        total_order_amount = Sum('total'),
        total_discount=Sum('discount')
    )

    context = {
        'orders':orders,
        'total':total,
        'start_date':start_date,
        'end_date':end_date
        }
    return render(request,"admin_panel/sales_report.html",context)

def export_pdf(request):
    orders, start_date, end_date = get_filtered_orders(request)
    total = orders.aggregate(
        sales_count = Count('id'),
        total_order_amount = Sum('total'),
        total_discount=Sum('discount')
    )

