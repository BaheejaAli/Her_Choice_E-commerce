from django.urls import path
from . import views

urlpatterns = [
    path("add/", views.add_to_cart, name = "add_to_cart"), 
    path("", views.cart, name="cart"), 
    path("update-quantity/", views.update_cart_quantity, name="update_cart_quantity"), 
    path("remove-item/", views.remove_cart_item, name="remove_cart_item"),
    path("checkout/", views.checkout, name="checkout"),


]
