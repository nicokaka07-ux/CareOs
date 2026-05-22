from django.db import models
from django.utils import timezone

class Drug(models.Model):
    CATEGORY_CHOICES = [
        ('antibiotic','Antibiotic'),('analgesic','Analgesic'),
        ('antiviral','Antiviral'),('antifungal','Antifungal'),
        ('supplement','Supplement'),('chronic','Chronic Disease'),('other','Other'),
    ]
    name           = models.CharField(max_length=200, unique=True)
    generic_name   = models.CharField(max_length=200, blank=True)
    category       = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    unit           = models.CharField(max_length=50)
    buying_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    minimum_stock  = models.PositiveIntegerField(default=10)
    expiry_date    = models.DateField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def is_low_stock(self): return self.stock_quantity <= self.minimum_stock
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date() if self.expiry_date else False
    @property
    def is_expiring_soon(self):
        if self.expiry_date:
            return 0 < (self.expiry_date - timezone.now().date()).days <= 30
        return False
    def __str__(self): return f"{self.name} ({self.stock_quantity} {self.unit})"
    class Meta: ordering = ['name']

class DispenseRecord(models.Model):
    prescription       = models.OneToOneField('clinical.Prescription', on_delete=models.CASCADE, related_name='dispense_record')
    drug               = models.ForeignKey(Drug, on_delete=models.SET_NULL, null=True)
    pharmacist         = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True)
    quantity_dispensed = models.PositiveIntegerField()
    dispensed_at       = models.DateTimeField(auto_now_add=True)
    notes              = models.TextField(blank=True)
    def __str__(self): return f"Dispensed {self.drug} x{self.quantity_dispensed}"