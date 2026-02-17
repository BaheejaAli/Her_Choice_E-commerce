from django.db import models
from django.utils import timezone
from brandsandcategories.models import Category
from django.conf import settings
import random
import string
from django.core.exceptions import ValidationError
from django.conf import settings

TARGET_TYPE_CHOICES = (
    ('product', 'Product'),
    ('category', 'Category'),
)


class Offer(models.Model):
    name = models.CharField(max_length=200)
    offer_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    discount_percentage = models.PositiveSmallIntegerField(default=0)
    product = models.ManyToManyField(
        'products.Product', blank=True, related_name='product_offers')
    category = models.ManyToManyField(
        Category, blank=True, related_name='category_offers')

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        now = timezone.now()
        return (self.is_active and self.start_at <= now and (self.end_at is None or self.end_at >= now))

    def __str__(self):
        if self.product.exists():
            target = ", ".join([p.name for p in self.product.all()])
        elif self.category.exists():
            target = ", ".join([c.name for c in self.category.all()])
        else:
            target = "No Target"


        return f"{self.name} - {target}"
    
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Referral(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="referral_profile")
    referral_code = models.CharField(max_length=10, default=generate_referral_code, unique=True, db_index=True)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email}-{self.referral_code}" 
    

class ReferralUsage(models.Model):
    class Status(models.TextChoices):
        REWARDED = 'Rewarded', 'Rewarded'
        PENDING = 'Pending', 'Pending'

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_given')
    receiver = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_received')
    
    referrer_reward_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    receiver_reward_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)

    
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receiver.email} used {self.referrer.email}'s code"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            if self.referrer == self.receiver:
                raise ValueError("User cannot use their own referral code.")

        super().save(*args, **kwargs)

# for the admin side
class ReferralReward(models.Model):
    referrer_amount = models.DecimalField(max_digits=10, decimal_places=2)
    receiver_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Only one active reward at a time
        if self.is_active:
            ReferralReward.objects.exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Referrer: ₹{self.referrer_amount} | Receiver: ₹{self.receiver_amount}"
    

class Coupon(models.Model):
    code = models.CharField( max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField()
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField( max_digits=10, decimal_places=2, default=0)
    max_usage_per_user = models.PositiveIntegerField(default=1)

    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()

    is_active = models.BooleanField(default=True)   
    limit = models.PositiveIntegerField(default=50)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"
        

    def clean(self):
        if not (1 <= self.discount_percentage <= 100):
            raise ValidationError("Discount must be between 1 and 100 percent.")
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValidationError("End date (valid_to) must be after start date (valid_from).")


    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def is_valid(self, cart_total, user):
        now = timezone.now()

        if not self.is_active:
            return False

        if not (self.valid_from <= now <= self.valid_to):
            return False

        if self.used_count >= self.limit:
            return False

        if cart_total < self.minimum_amount:
            return False

        usage = CouponUsage.objects.filter(user=user, coupon=self).first()
        if usage and usage.used_count >= self.max_usage_per_user:
            return False

        return True
    
    @property
    def status(self):
        now = timezone.now()

        if not self.is_active:
            return "inactive"

        if now < self.valid_from:
            return "scheduled"

        if now > self.valid_to:
            return "expired"

        return "active"


    def __str__(self):
        return f"{self.code} ({self.discount_percentage}% OFF)"
    
    def calculate_discount(self, cart_total):
        discount = (cart_total * self.discount_percentage) / 100
        if self.max_discount_amount and self.max_discount_amount > 0:
            discount = min(discount, self.max_discount_amount)
        return discount
    

class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'coupon'], name='unique_user_coupon')
    ]

    def __str__(self):
        return f"{self.user.email} - {self.coupon.code}"


    
   
    
    
