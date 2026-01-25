from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from orders.models import Order,OrderItem
from django.db.models import Q

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

def order_invoice(request,order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__variant"), id= order_id, user=request.user)

    return render(request, "orders/order_invoice.html",{"order":order})
