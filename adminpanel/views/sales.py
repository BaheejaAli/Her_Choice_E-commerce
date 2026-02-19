from django.shortcuts import render
from django.db.models import Count, Sum
from orders.models import Order
from django.utils import timezone
from datetime import timedelta
import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse
from django.core.paginator import Paginator
from datetime import datetime
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import render_to_string
from weasyprint import HTML
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache

def is_admin(user):
    return user.is_staff or user.is_superuser


def get_filtered_orders(request):
    date_range = request.GET.get('date_range','month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    orders = Order.objects.exclude(status__in=['cancelled','failed']).order_by("-created_at")

    today = timezone.now().date()
    if date_range == 'today':
        start_date = end_date = today
        orders = orders.filter(created_at__date=today)

    elif date_range == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
        orders = orders.filter(created_at__date__gte=start_date)

    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
        orders = orders.filter(created_at__date__gte=start_date)

    elif date_range == 'year':
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
        orders = orders.filter(created_at__year=today.year)

    elif date_range == 'custom' and start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    return orders, start_date, end_date

@login_required
@user_passes_test(is_admin)
@never_cache
def sales_report(request):
    orders, start_date, end_date = get_filtered_orders(request)
    total = orders.aggregate(
        sales_count = Count('id'),
        total_order_amount = Sum('total'),
        total_discount=Sum('discount')
    )

    paginator = Paginator(orders, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj, 
        'is_paginated': page_obj.has_other_pages(),
        'page_range': paginator.get_elided_page_range(page_obj.number),
        'total':total,
        'start_date':start_date,
        'end_date':end_date
        }
    return render(request,"admin_panel/sales_report.html",context)

@login_required
@user_passes_test(is_admin)
@never_cache
def export_pdf(request):
    orders, start_date, end_date = get_filtered_orders(request)

    total = orders.aggregate(
        sales_count=Count('id'),
        total_order_amount=Sum('total'),
        total_discount=Sum('discount')
    )

    html_string = render_to_string("admin_panel/sales_report_pdf.html", {
        "orders": orders,
        "start_date": start_date,
        "end_date": end_date,
        "total": total,
        "now": timezone.now()
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=sales_report.pdf"

    HTML(string=html_string).write_pdf(response)

    return response

@login_required
@user_passes_test(is_admin)
@never_cache
def export_excel(request):
    orders, start_date, end_date = get_filtered_orders(request)

    # Create workbook
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    headers = ["Order ID", "Customer", "Total", "Discount", "Status", "Date"]

    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)

    # Add data rows
    for row_num, order in enumerate(orders, 2):
        sheet.cell(row=row_num, column=1).value = order.id
        sheet.cell(row=row_num, column=2).value = order.user.get_full_name if order.user else "Guest"
        sheet.cell(row=row_num, column=3).value = float(order.total)
        sheet.cell(row=row_num, column=4).value = float(order.discount or 0)
        sheet.cell(row=row_num, column=5).value = order.status
        sheet.cell(row=row_num, column=6).value = order.created_at.strftime("%Y-%m-%d")

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=sales_report.xlsx"

    workbook.save(response)
    return response



