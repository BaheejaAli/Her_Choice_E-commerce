from django.shortcuts import render, get_object_or_404, redirect
from orders.models import Order, OrderItem
from django.db.models import Q, F, Count, Sum
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from products.models import ProductVariant
from wallet.models import Wallet, WalletTransaction
from decimal import Decimal
from django.contrib.auth.decorators import user_passes_test

def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
@never_cache
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

@require_POST
@login_required
@user_passes_test(is_admin)
@never_cache
def update_order_status(request, order_id):
    new_status = request.POST.get("status")
    order = get_object_or_404(Order, id=order_id)
    
    total_refunded_now = Decimal('0')

    with transaction.atomic():
        if new_status:
            current_status = order.status.lower()
            if new_status != current_status:
                if new_status not in order.ADMIN_STATUS_FLOW.get(current_status, []):
                    messages.error(request, f"Invalid move: {current_status} to {new_status}")   
                    return redirect("order_view_details", order_id=order.id)
                
                order.status = new_status

                # DELIVERY LOGIC
                if new_status == 'delivered':
                    order.items.exclude(status='cancelled').update(status='delivered', delivered_at=timezone.now())
                    if order.payment_method == 'cod':
                        order.payment_status = 'paid'

                # CANCELLATION LOGIC
                elif new_status == 'cancelled':
                    all_items = order.items.all()
                    total_items_count = all_items.count()
                    items_to_cancel = all_items.exclude(status='cancelled')
                    total_refunded_now = Decimal('0')
                    can_refund = order.payment_status in ['paid', 'partially_refunded']

                    for item in items_to_cancel:
                        item.status = 'cancelled'
                        item.cancelled_at = timezone.now()
                        item.save()

                        ProductVariant.objects.filter(id=item.variant.id).update(stock=F('stock') + item.quantity)
                        
                        if can_refund:
                            item_refund = order.calculate_item_refund(item)
                            total_refunded_now += item_refund

                    # Check for full cancellation to refund delivery charge
                    cancelled_items_count = all_items.filter(status='cancelled').count()
                    is_full_cancellation = (cancelled_items_count == total_items_count)
                    
                    if can_refund and is_full_cancellation:
                        total_refunded_now += order.delivery_charge

                    
                    if total_refunded_now > 0:
                        # to prevent over refund
                        already_refunded = WalletTransaction.objects.filter(
                            wallet__user=order.user,
                            description__icontains=order.orderid,
                            transaction_type="REFUND"
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                        
                        remaining_allowed = order.total - already_refunded
                        if remaining_allowed <= 0:
                            total_refunded_now = Decimal('0.00') 
                        elif total_refunded_now > remaining_allowed: 
                            total_refunded_now = remaining_allowed
                    
                    if total_refunded_now > 0:
                        wallet, _ = Wallet.objects.get_or_create(user=order.user)
                        Wallet.objects.filter(id=wallet.id).update(balance=F('balance') + total_refunded_now)

                        WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=total_refunded_now,
                            transaction_type='REFUND',
                            description=f"Refund for cancelled items (Order: {order.orderid})"
                        )

                    # 4. Sync Payment Status after cancellation
                    stats = order.items.aggregate(
                        total=Count('id'),
                        cancelled=Count('id', filter=Q(status='cancelled')),
                        returned=Count('id', filter=Q(return_status='returned'))
                    )

                    if (stats['cancelled'] + stats['returned']) == stats['total']:
                        order.payment_status = 'refunded'
                    elif stats['cancelled'] > 0 and order.payment_status in ['paid', 'partially_refunded']:
                        order.payment_status = 'partially_refunded'

                    if total_refunded_now > 0:
                        messages.success(request, f"₹ {total_refunded_now} refunded to wallet due to cancellation.")


                # RETURN & REFUND LOGIC
                elif new_status == 'returned':
                    all_items = order.items.all()
                    total_items_count = all_items.count()
                    approved_items = all_items.filter(return_status='return_approved')
                    total_refunded_now = Decimal('0')
                    can_refund = order.payment_status in ['paid', 'partially_refunded']

                    for item in approved_items:
                        item.return_status = 'returned'
                        item.returned_at = timezone.now()
                        item.save()
                        
                        # Restore Stock
                        ProductVariant.objects.filter(id=item.variant.id).update(stock=F('stock') + item.quantity)
                        
                        if can_refund:
                            item_refund = order.calculate_item_refund(item)
                            total_refunded_now += item_refund
                    
                    # Check if EVERYTHING is either returned or cancelled for full refund (including delivery)
                    finished_items_count = all_items.filter(Q(return_status='returned') | Q(status='cancelled')).count()
                    is_completely_done = (finished_items_count == total_items_count)
                    
                    if can_refund and is_completely_done:
                        total_refunded_now += order.delivery_charge

                    # to prevent over refund
                    if total_refunded_now > 0:
                        already_refunded = WalletTransaction.objects.filter(
                            wallet__user=order.user,
                            description__icontains=order.orderid,
                            transaction_type="REFUND"
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                        
                        remaining_allowed = order.total - already_refunded
                        if remaining_allowed <= 0:
                            total_refunded_now = Decimal('0.00') 
                        elif total_refunded_now > remaining_allowed: 
                            total_refunded_now = remaining_allowed

                    if total_refunded_now > 0:
                        wallet, _ = Wallet.objects.get_or_create(user=order.user)
                        Wallet.objects.filter(id=wallet.id).update(balance=F('balance') + total_refunded_now)

                        WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=total_refunded_now,
                            transaction_type='REFUND',
                            description=f"Refund for returned/cancelled items (Order: {order.orderid})"
                        )

                    # Recalculate Payment Status automatically
                    stats = order.items.aggregate(
                        total=Count('id'),
                        returned=Count('id', filter=Q(return_status='returned')),
                        cancelled=Count('id', filter=Q(status='cancelled'))
                    )
                    
                    if (stats['returned'] + stats['cancelled']) == stats['total']:
                        order.payment_status = 'refunded'
                    elif stats['returned'] > 0:
                        order.payment_status = 'partially_refunded'

                    if total_refunded_now > 0:
                        messages.success(request, f"₹ {total_refunded_now} refunded to wallet.")

                elif new_status == 'return_approved':
                    order.items.filter(return_status='return_requested').update(return_status='return_approved')
                
                elif new_status == 'return_rejected':
                    order.items.filter(return_status='return_requested').update(return_status='return_rejected')

        # Save the automated changes
        order.save()
        order.update_order_status()


    messages.success(request, f"Order #{order.orderid} updated successfully.")
    return redirect("order_view_details", order_id=order.id)

@login_required
@user_passes_test(is_admin)
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

@login_required
@user_passes_test(is_admin)
@never_cache
def stock_management(request):
    query = request.GET.get('q','')
    stock_status = request.GET.get('stock_status', '')
    variants = ProductVariant.objects.select_related('product','size','color').all()

    if query:
        variants = variants.filter(
            Q(product__name__icontains=query) |
            Q(sku__icontains=query)
        )

    if stock_status == 'all':
        variants = variants.all()
    elif stock_status == 'in_stock':
        variants = variants.filter(stock__gt=10)
    elif stock_status == 'low_stock':
        variants = variants.filter(stock__range=(1, 10))
    elif stock_status == 'out_of_stock':
        variants = variants.filter(stock=0)

    total_items = ProductVariant.objects.count()
    low_stock_count = ProductVariant.objects.filter(stock__gt=0, stock__lte=10).count()
    out_of_stock_count = ProductVariant.objects.filter(stock=0).count()

    paginator = Paginator(variants, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "variants": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "page_range": paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        ),
        'total_items': total_items,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'query': query,
        'status': stock_status,
    }
    return render(request, "admin_panel/stock.html",context)


