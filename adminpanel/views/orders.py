from django.shortcuts import render, get_object_or_404, redirect
from orders.models import Order, OrderItem
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction


@never_cache
@login_required
def order_management(request):
    status = request.GET.get("status")
    query = request.GET.get("q", "").strip().lower()
    orders = Order.objects.select_related("user").order_by("-created_at")
    if query:
        orders = orders.filter(
            Q(orderid__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(payment_method__icontains=query)
        )
    if status:
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "orders": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "page_range": paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        ),
        "status": status,
        "query": query,
    }

    return render(request, "admin_panel/order_management.html", context)


@login_required
@never_cache
@require_POST
def update_order_status(request, order_id):

    new_status = request.POST.get("status")
    new_payment_status = request.POST.get("payment_status")

    if not order_id:
        messages.error(request, "Missing order identifier.")
        return redirect("order_management")

    order = get_object_or_404(Order, id=order_id)
    with transaction.atomic():
        if new_status:
            current_status = order.status.lower()
            if new_status != current_status:
                if new_status not in order.ADMIN_STATUS_FLOW.get(current_status, []):
                    messages.error(request, f"Invalid move: {current_status} to {new_status}")   
                    return redirect("order_view_details", id=order_id)
                
                order.status = new_status
                
                if new_status in ['shipped', 'delivered', 'cancelled']:
                    active_items = order.items.exclude(status='cancelled').exclude(
                        return_status__in=['return_requested', 'return_approved', 'returned'])
                    active_items.update(status=new_status)

                    if new_status == 'delivered':
                        active_items.update(delivered_at=timezone.now())

                    if new_status == 'cancelled':
                        active_items.update(cancelled_at=timezone.now())

                elif new_status == 'return_approved':
                    order.items.filter(return_status='return_requested').update(return_status='return_approved')
                
                elif new_status == 'return_rejected':
                    order.items.filter(return_status='return_requested').update(return_status='return_rejected')
                
                elif new_status == 'returned':
                    approved_items = order.items.filter(return_status='return_approved')
                    for item in approved_items:
                        item.return_status = 'returned'
                        item.save()

        if new_payment_status:
            order.payment_status = new_payment_status

        order.save()
        order.update_order_status()
    messages.success(request, f"Order #{order.orderid} updated successfully.")
    return redirect("order_view_details", order_id=order.id)


@login_required
@never_cache
def order_view_details(request, order_id):
    order = get_object_or_404(Order.objects.select_related("user", "address", "billing_address")
                              .prefetch_related("items__variant", "items__variant__product", "items__variant__images"),
                              id=order_id)
 
    current_status = order.status.lower()
    allowed_next_statuses = order.ADMIN_STATUS_FLOW.get(current_status, [])
    allowed_statuses = [current_status] + allowed_next_statuses
    return render(request, "admin_panel/order_view_details.html", {
        "order": order,
        "user": order.user,
        "allowed_statuses": allowed_statuses,
        "order_statuses": Order.STATUS_CHOICES,
        "payment_statuses": Order.PAYMENT_STATUS_CHOICES
    })
