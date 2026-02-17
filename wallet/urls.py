from django.urls import path
from . import views
urlpatterns = [
    path("wallet/", views.wallet_dashboard, name="wallet_dashboard"),
    path("wallet/add-money/", views.add_money, name="add_money"),
    path('wallet/verify/', views.verify_payment, name='verify_payment'),
]

