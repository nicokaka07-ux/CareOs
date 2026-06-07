
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('insurance', 'Pending Insurance'),
        ('void', 'Void'),
    ]

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False
    )

    patient = models.ForeignKey(
        'opd.Patient',
        on_delete=models.CASCADE,
        related_name='invoices'
    )

    appointment = models.OneToOneField(
        'opd.Appointment',
        on_delete=models.CASCADE,
        related_name='invoice',
        null=True,
        blank=True
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    insurance_cover = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    insurance_provider = models.CharField(
        max_length=100,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unpaid'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        'accounts.StaffUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            today = timezone.now()
            count = Invoice.objects.count() + 1
            self.invoice_number = (
                f"INV-{today.strftime('%Y%m%d')}-{count:06d}"
            )

        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        total = self.items.aggregate(
            total=Sum(
                models.F('quantity') *
                models.F('unit_price')
            )
        )['total']

        return total or Decimal('0.00')

    @property
    def total(self):
        return (
            self.subtotal
            - self.discount
            - self.insurance_cover
        )

    @property
    def amount_paid(self):
        total = self.payments.aggregate(
            total=Sum('amount')
        )['total']

        return total or Decimal('0.00')

    @property
    def balance(self):
        return self.total - self.amount_paid

    def update_status(self):

        if self.amount_paid >= self.total:
            self.status = 'paid'

        elif self.amount_paid > 0:
            self.status = 'partial'

        else:
            self.status = 'unpaid'

        self.save(update_fields=['status'])

    def __str__(self):
        return f"{self.invoice_number}"

    class Meta:
        ordering = ['-created_at']


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )

    description = models.CharField(
        max_length=255
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    @property
    def total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description


class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('insurance', 'Insurance'),
        ('cheque', 'Cheque'),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    received_by = models.ForeignKey(
        'accounts.StaffUser',
        on_delete=models.SET_NULL,
        null=True
    )

    paid_at = models.DateTimeField(
        auto_now_add=True
    )

    notes = models.TextField(
        blank=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.invoice.update_status()

    def __str__(self):
        return (
            f"{self.get_method_display()} "
            f"KES {self.amount}"
        )


class MpesaTransaction(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='mpesa_transactions'
    )

    phone_number = models.CharField(
        max_length=15
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    checkout_request_id = models.CharField(
        max_length=200,
        blank=True
    )

    merchant_request_id = models.CharField(
        max_length=200,
        blank=True
    )

    mpesa_receipt = models.CharField(
        max_length=100,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    result_desc = models.TextField(
        blank=True
    )

    initiated_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def mark_success(self, receipt_number):

        self.status = 'success'
        self.mpesa_receipt = receipt_number
        self.completed_at = timezone.now()

        self.save()

        Payment.objects.create(
            invoice=self.invoice,
            method='mpesa',
            amount=self.amount,
            reference=receipt_number
        )

    def __str__(self):
        return (
            f"{self.phone_number} - "
            f"KES {self.amount}"
        )

    class Meta:
        ordering = ['-initiated_at']


class Receipt(models.Model):
    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='receipts'
    )

    content_html = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='receipts/', blank=True, null=True)

    generated_by = models.ForeignKey(
        'accounts.StaffUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    generated_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            today = timezone.now()
            count = Receipt.objects.count() + 1
            self.receipt_number = f"RCT-{today.strftime('%Y%m%d')}-{count:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} — {self.invoice.invoice_number}"

    class Meta:
        ordering = ['-generated_at']
