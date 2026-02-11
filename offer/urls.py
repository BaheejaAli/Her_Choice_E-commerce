from django.urls import path
from .views import apply_referral_page
urlpatterns = [
    path("apply-referral-page/", apply_referral_page, name="apply_referral_page")
]
