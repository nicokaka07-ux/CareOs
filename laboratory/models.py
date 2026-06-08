from django.db import models

class LabTestCatalog(models.Model):
    """Global price book and catalog for specific laboratory tests."""
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)  # e.g., CBC, FLUIDS, WIDAL
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    normal_range = models.TextField(help_text="Reference limits (e.g., Male: 13.5-17.5 g/dL)")

    def __str__(self):
        return f"{self.code} - {self.name}"

class LabOrder(models.Model):
    """Tracks individual laboratory requests linked directly back to patients."""
    STATUS_CHOICES = [
        ('ordered', 'Awaiting Sample'),
        ('processing', 'Processing'),
        ('completed', 'Results Released'),
    ]
    # Updated related_name to avoid clashes with clinical.LabOrder
    patient = models.ForeignKey(
        'opd.Patient', 
        on_delete=models.CASCADE, 
        related_name='specialized_lab_orders'
    )
    # Updated related_name to avoid clashes with clinical.LabOrder
    appointment = models.ForeignKey(
        'opd.Appointment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='specialized_lab_appointments'
    )
    test = models.ForeignKey(LabTestCatalog, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
    result_values = models.TextField(blank=True, help_text="Observed patient values")
    lab_notes = models.TextField(blank=True, help_text="Pathologist comments")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.test.code}"
