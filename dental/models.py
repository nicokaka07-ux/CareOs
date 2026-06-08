from django.db import models

class DentalProcedureCatalog(models.Model):
    """Catalog item pricing for extractions, cleanings, or cosmetic alignments."""
    name = models.CharField(max_length=150, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class DentalEncounter(models.Model):
    """Captures specific individual dental procedures performed on localized target teeth."""
    patient = models.ForeignKey(
        'opd.Patient', 
        on_delete=models.CASCADE, 
        related_name='specialized_dental_encounters'
    )
    appointment = models.ForeignKey(
        'opd.Appointment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='specialized_dental_appointments'
    )
    procedure = models.ForeignKey(DentalProcedureCatalog, on_delete=models.PROTECT)
    tooth_number = models.CharField(max_length=50, blank=True, help_text="Tooth identity notation system (e.g. 14, 32)")
    clinical_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dental Encounter #{self.id} - {self.procedure.name}"