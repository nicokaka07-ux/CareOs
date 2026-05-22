from django.db import models

class TriageRecord(models.Model):
    appointment              = models.OneToOneField('opd.Appointment', on_delete=models.CASCADE, related_name='triage')
    patient                  = models.ForeignKey('opd.Patient', on_delete=models.CASCADE, related_name='triages')
    nurse                    = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True, related_name='triage_records')
    blood_pressure_systolic  = models.PositiveIntegerField()
    blood_pressure_diastolic = models.PositiveIntegerField()
    temperature              = models.DecimalField(max_digits=4, decimal_places=1)
    heart_rate               = models.PositiveIntegerField()
    respiratory_rate         = models.PositiveIntegerField()
    oxygen_saturation        = models.PositiveIntegerField()
    weight                   = models.DecimalField(max_digits=5, decimal_places=1)
    height                   = models.DecimalField(max_digits=5, decimal_places=1)
    pain_scale               = models.PositiveIntegerField(default=0)
    chief_complaint          = models.TextField()
    nurse_notes              = models.TextField(blank=True)
    recorded_at              = models.DateTimeField(auto_now_add=True)

    @property
    def bmi(self):
        if self.height and self.weight:
            h = float(self.height)/100
            return round(float(self.weight)/(h*h),1)
        return None

    @property
    def blood_pressure(self):
        return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"

    class Meta: ordering = ['-recorded_at']

class Consultation(models.Model):
    appointment          = models.OneToOneField('opd.Appointment', on_delete=models.CASCADE, related_name='consultation')
    patient              = models.ForeignKey('opd.Patient', on_delete=models.CASCADE, related_name='consultations')
    doctor               = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True, related_name='consultations')
    presenting_complaint = models.TextField()
    history_of_illness   = models.TextField(blank=True)
    examination_findings = models.TextField(blank=True)
    diagnosis            = models.TextField()
    treatment_plan       = models.TextField(blank=True)
    doctor_notes         = models.TextField(blank=True)
    follow_up_date       = models.DateField(null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)
    class Meta: ordering = ['-created_at']

class LabOrder(models.Model):
    STATUS = [('ordered','Ordered'),('processing','Processing'),
              ('completed','Completed'),('cancelled','Cancelled')]
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='lab_orders')
    patient      = models.ForeignKey('opd.Patient', on_delete=models.CASCADE, related_name='lab_orders')
    doctor       = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True, related_name='lab_orders')
    test_name    = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS, default='ordered')
    result       = models.TextField(blank=True)
    ordered_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-ordered_at']

class Prescription(models.Model):
    STATUS = [('pending','Pending'),('dispensed','Dispensed'),('cancelled','Cancelled')]
    consultation    = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='prescriptions')
    patient         = models.ForeignKey('opd.Patient', on_delete=models.CASCADE, related_name='prescriptions')
    doctor          = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL, null=True, related_name='prescriptions')
    medication_name = models.CharField(max_length=200)
    dosage          = models.CharField(max_length=100)
    frequency       = models.CharField(max_length=100)
    duration        = models.CharField(max_length=100)
    instructions    = models.TextField(blank=True)
    quantity        = models.PositiveIntegerField(default=1)
    status          = models.CharField(max_length=20, choices=STATUS, default='pending')
    prescribed_at   = models.DateTimeField(auto_now_add=True)
    dispensed_at    = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-prescribed_at']