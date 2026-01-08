from django.db import models,transaction
from django.conf import settings

# Create your models here.

class UserAddress(models.Model):
    ADDRESS_TYPES = (
        ('home','Home'),
        ('work','Work'),
        ('other','Other'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    address_line_1 = models.CharField( max_length=255)
    address_line_2 = models.CharField( max_length=255, blank=True, null=True)
    city = models.CharField( max_length=100)
    state = models.CharField( max_length=100)
    pincode = models.CharField( max_length=10)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_type} - {self.user.email}"
    
    # Ensure only one default address per user
    def save(self, *args, **kwargs):
        if self.is_default:
            # Use atomic transaction to ensure data integrity
            with transaction.atomic():
                UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
                super().save(*args, **kwargs)
        else:
            # If this is the user's ONLY address, make it default anyway
            if not UserAddress.objects.filter(user=self.user).exists():
                self.is_default = True
            super().save(*args, **kwargs)
