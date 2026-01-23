from django.shortcuts import render, get_object_or_404
from orders.models import Order
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@never_cache
@login_required
def order_management(request):
    status = request.GET.get("status")
    query = request.GET.get("q")
    orders= Order.objects.select_related("user").order_by("-created_at")
    if query:
        orders = orders.filter(
            Q(orderid__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) 
        )
    if status:
        orders = orders.filter(status=status)
    return render(request,"admin_panel/order_management.html",{"orders":orders,"status":status,"query":query})

@login_required
@never_cache
def update_order_status(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"},status=400)
    order_id = request.POST.get("order_id")
    status =  request.POST.get("status")
    if not status or not order_id:
        return JsonResponse({"success": False, "error": "Missing data"},status=400)
    
    try:
      order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"},status=400)

    order.status = status
    if status == "delivered" and not order.delivered_at:
        order.delivered_at = timezone.now()

    order.save(update_fields=["status"])
    return JsonResponse({"success":True, "status":order.get_status_display()},status=200)
    
@login_required
@never_cache
def order_view_details(request, order_id):
    order = get_object_or_404(Order.objects.select_related("user","address","billing_address")
                              .prefetch_related("items__variant","items__variant__product","items__variant__images"),
                              id=order_id)
    return render(request, "admin_panel/order_view_details.html", {"order":order, "user":order.user})



    