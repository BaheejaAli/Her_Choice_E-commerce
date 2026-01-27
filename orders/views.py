from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from orders.models import Order,OrderItem
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

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
    return render(request,"orders/order_history.html",{"orders":orders, "status":status, "query":query, "sort":sort})


@login_required
def order_details(request,order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__variant"),
                               id= order_id, user= request.user)
    context = {
        "order":order,   
    }
    return render(request, "orders/order_details.html",context)

@login_required
def order_invoice(request,order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__variant"), id= order_id, user=request.user)

    return render(request, "orders/order_invoice.html",{"order":order})

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id = order_id, user = request.user)
    if order.status not in ["pending","processing"]:
        messages.error(request,"This message cannot be cancelled.")
        return redirect("order_details", order_id=order.id)
    
    if request.method == "POST":
        cancel_reason = request.POST.get("cancel_reason", "").strip()
        
    for item in order.items.all():
        if item.status != "cancelled":
            variant = item.variant
            variant.stock += item.quantity
            variant.save(update_fields=["stock"])

            item.status = "cancelled"
            item.cancelled = True
            item.cancelled_at = timezone.now()
            item.save()
    
    order.status ="cancelled"
    order.cancel_reason = cancel_reason
    order.save(update_fields=["status","updated_at"])

    messages.success(request, "Your order has been cancelled successfully.")
    return redirect("order_details", order_id=order.id)


