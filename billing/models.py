from django.db import models
from django.utils import timezone

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid','Unpaid'),('partial','Partially Paid'),
        ('paid','Paid'),('insurance','Pending Insurance'),('void','Void'),
    ]
    invoice_number   = models.CharField(max_length=20, unique=True, editable=False)
    patient          = models.ForeignKey('opd.Patient', on_delete=models.CASCADE, related_name='invoices')
    appointment      = models.OneToOneField('opd.Appointment', on_delete=models.CASCADE,
                                             related_name='invoice', null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_fee          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pharmacy_fee     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fee        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    created_by       = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                          null=True, related_name='created_invoices')

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            today = timezone.now()
            count = Invoice.objects.filter(created_at__date=today.date()).count() + 1
            self.invoice_number = f"INV-{today.strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self): return self.consultation_fee + self.lab_fee + self.pharmacy_fee + self.other_fee
    @property
    def total(self): return self.subtotal - self.discount
    @property
    def amount_paid(self): return sum(p.amount for p in self.payments.all())
    @property
    def balance(self): return self.total - self.amount_paid
    def __str__(self): return f"{self.invoice_number} — {self.patient}"
    class Meta: ordering = ['-created_at']

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash','Cash'),('mpesa','M-Pesa'),('card','Card'),
        ('insurance','Insurance'),('cheque','Cheque'),
    ]
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    method      = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    reference   = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True)
    paid_at     = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True)
    def __str__(self): return f"{self.get_method_display()} KES {self.amount}"

class MpesaTransaction(models.Model):
    STATUS_CHOICES = [('pending','Pending'),('success','Success'),
                      ('failed','Failed'),('cancelled','Cancelled')]
    invoice             = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='mpesa_transactions')
    phone_number        = models.CharField(max_length=15)
    amount              = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_request_id = models.CharField(max_length=200, blank=True)
    merchant_request_id = models.CharField(max_length=200, blank=True)
    mpesa_receipt       = models.CharField(max_length=100, blank=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result_desc         = models.TextField(blank=True)
    initiated_at        = models.DateTimeField(auto_now_add=True)
    completed_at        = models.DateTimeField(null=True, blank=True)
    def __str__(self): return f"STK {self.phone_number} — KES {self.amount} — {self.status}"
    class Meta: ordering = ['-initiated_at']