from django.db import models
from django.conf import settings
from decimal import Decimal

# Create your models here.
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def add_funds(self,amount):
        if amount>0:
            self.balance += Decimal(str(amount))
            self.save()
            return True
        return False
    
    def deduct_funds(self, amount):
        amount = Decimal(str(amount))
        if 0 < amount <= self.balance:
            self.balance -= amount
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.user.email} Wallet"


class WalletTransaction(models.Model):
    TRANSACTION_TYPE = (
        ('DEPOSIT', 'Deposit'),
        ('PAYMENT', 'Order Payment'),
        ('REFERRAL', 'Referral Reward'),
        ('REFUND', 'Refund'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} - {self.amount}"
    
    class Meta:
        ordering = ['-created_at']
