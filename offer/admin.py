from django.contrib import admin
from .models import ReferralReward, Referral, ReferralUsage, Coupon

admin.site.register(Referral)
admin.site.register(ReferralReward)
admin.site.register(ReferralUsage)
admin.site.register(Coupon)
