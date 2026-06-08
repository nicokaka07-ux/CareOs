from django.db import models

class OpticalServiceCatalog(models.Model):
    """Catalog item itemizing specific frames, replacement lenses, or specialty refractions."""
    name = models.CharField(max_length=150, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class OpticalPrescription(models.Model):
    """Stores full optometric physical evaluations for patient refractive errors."""
    patient = models.ForeignKey(
        'opd.Patient', 
        on_delete=models.CASCADE, 
        related_name='specialized_optical_prescriptions'
    )
    appointment = models.ForeignKey(
        'opd.Appointment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='specialized_optical_appointments'
    )
    service_item = models.ForeignKey(OpticalServiceCatalog, on_delete=models.PROTECT, null=True, blank=True)
    
    # Left and Right eye structural measurement grids
    od_sphere = models.CharField(max_length=10, blank=True, verbose_name="OD Sphere")
    od_cylinder = models.CharField(max_length=10, blank=True, verbose_name="OD Cylinder")
    od_axis = models.CharField(max_length=10, blank=True, verbose_name="OD Axis")
    
    os_sphere = models.CharField(max_length=10, blank=True, verbose_name="OS Sphere")
    os_cylinder = models.CharField(max_length=10, blank=True, verbose_name="OS Cylinder")
    os_axis = models.CharField(max_length=10, blank=True, verbose_name="OS Axis")
    
    pd = models.CharField(max_length=10, blank=True, verbose_name="Pupillary Distance")
    clinical_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Optical Rx #{self.id} - {self.patient}"