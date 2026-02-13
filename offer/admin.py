from django.contrib import admin
from .models import ReferralReward, Referral, ReferralUsage

admin.site.register(Referral)
admin.site.register(ReferralReward)
admin.site.register(ReferralUsage)
