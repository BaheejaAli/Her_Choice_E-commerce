from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from orders.models import Order,OrderItem
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
from decimal import Decimal
from wallet.models import Wallet, WalletTransaction
from django.core.paginator import Paginator
from django.db.models import F

# Create your views here.
@login_required
def order_history(request):
    orders = Order.objects.filter(user= request.user)
    status = request.GET.get("status")
    
    if status:
        orders = orders.filter(status=status)
    query = request.GET.get("q")
    if query:
        orders = orders.filter(
            Q(orderid__icontains= query)|Q(items__variant__product__name__icontains=query)
        ).distinct()
    sort = request.GET.get("sort","recent")
    if sort == "oldest":
        orders = orders.order_by("created_at")
    elif sort == "price-high":
        orders = orders.order_by("-total")
    elif sort == "price-low":
        orders = orders.order_by("total")
    else:
        orders = orders.order_by("-created_at")
    
    # Pagination
    paginator = Paginator(orders, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number)
    
    return render(request,"orders/order_history.html",{
        "orders":page_obj.object_list, 
        "page_obj":page_obj,
        "page_range":page_range,
        "is_paginated":page_obj.has_other_pages(),
        "status":status, 
        "query":query, 
        "sort":sort
    })


@login_required
def order_details(request,order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__variant__size", "items__variant__color"),
                               id= order_id, user= request.user)
    context = {
        "order":order,   
    }
    return render(request, "orders/order_details.html",context)

@login_required
def download_invoice_pdf(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__variant__size", "items__variant__color"), id=order_id, user=request.user)

    html_string = render_to_string("orders/order_invoice_pdf.html", {"order": order})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=invoice_{order.orderid}.pdf"

    HTML(string=html_string).write_pdf(response)

    return response

@login_required
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status not in ["pending", "processing", "partially_cancelled"]:
        messages.error(request, "This order cannot be cancelled anymore.")
        return redirect("order_details", order_id=order.id)
    
    if request.method == "POST":
        selected_item_ids = request.POST.getlist('selected_items')
        cancel_reason = request.POST.get("cancel_reason", "").strip()

        if not selected_item_ids:
            messages.error(request, "No items were selected for cancellation.")
            return redirect("order_details", order_id=order.id)

        with transaction.atomic():
            all_items = order.items.all()
            total_items_count = all_items.count()
            
            items_to_cancel = all_items.filter(id__in=selected_item_ids).exclude(status="cancelled")
            
            total_refund_amount = Decimal('0.00')
            can_refund = order.payment_status in ["paid", "partially_refunded"] and order.payment_method in ["razorpay", "wallet"]

            for item in items_to_cancel:
                # Update Inventory Atomically
                from products.models import ProductVariant
                ProductVariant.objects.filter(id=item.variant.id).update(stock=F("stock") + item.quantity)

                # Update Item Status
                item.status = "cancelled"
                item.cancel_reason = cancel_reason 
                item.cancelled_at = timezone.now()
                item.save()

                if can_refund:
                    item_refund = order.calculate_item_refund(item)
                    total_refund_amount += item_refund

            finished_items_count = all_items.filter(Q(return_status='returned') | Q(status='cancelled')).count()
            is_full_completion = (finished_items_count == total_items_count)

            if can_refund and is_full_completion:
                already_refunded = WalletTransaction.objects.filter(
                    wallet__user=order.user,
                    description__icontains=order.orderid,
                    transaction_type="REFUND"
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                max_refundable_amount = order.total - order.delivery_charge
                remaining_to_refund = max_refundable_amount - already_refunded
              
                if items_to_cancel.exists():
                    total_refund_amount = max(remaining_to_refund, Decimal('0.00'))

            if total_refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
                Wallet.objects.filter(id=wallet.id).update(balance=F('balance') + total_refund_amount)

                WalletTransaction.objects.create(
                    wallet = wallet,
                    amount = total_refund_amount,
                    transaction_type = "REFUND",
                    description=f"Refund for cancelled items in Order {order.orderid}"
                )
                
                if is_full_completion:
                    order.payment_status = "refunded"
                else:
                    order.payment_status = "partially_refunded"

            if is_full_completion:
                order.status = "cancelled" if all_items.filter(status='cancelled').count() == total_items_count else order.status
                messages.success(request, "Your order items have been cancelled successfully.")
            else:
                order.status = "partially_cancelled"
                messages.success(request, f"Successfully cancelled {items_to_cancel.count()} item(s).")
            
            order.save(update_fields=["status", "payment_status", "updated_at"])          
        return redirect("order_details", order_id=order.id)
    

@login_required
@require_POST
def return_request(request, order_id):
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        reason = request.POST.get("return_reason")
        comment = request.POST.get("return_comment")

        item = get_object_or_404(OrderItem, id=item_id, order__id=order_id, order__user=request.user)

        if item.status == 'delivered' and item.return_status == 'none':
            item.return_status = 'return_requested'
            item.save()
            messages.success(request, f"Return request for {item.variant.product.name} has been submitted.")
        else:
            messages.error(request, "This item is not eligible for return.")

    return redirect("order_details", order_id=order_id)



       
