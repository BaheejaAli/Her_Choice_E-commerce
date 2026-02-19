from django.urls import path
from . import views
urlpatterns = [
    path("order_history/",views.order_history, name="order_history"),
    path("order-details/<int:order_id>/",views.order_details, name="order_details"),
    path("order-invoice-pdf/<int:order_id>/",views.download_invoice_pdf, name="download_invoice_pdf"),
    path("cancel/<int:order_id>/", views.cancel_order, name="cancel_order"),
    path("return/<int:order_id>/", views.return_request, name="return_request"),

    
]
