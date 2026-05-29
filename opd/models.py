from django.db import models
from django.utils import timezone

def generate_patient_id():
    year  = timezone.now().year
    count = Patient.objects.filter(created_at__year=year).count() + 1
    return f"COS-{year}-{count:05d}"

class Patient(models.Model):
    GENDER_CHOICES      = [('male','Male'),('female','Female'),('other','Other')]
    BLOOD_GROUP_CHOICES = [('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
                           ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-'),('unknown','Unknown')]

    patient_id    = models.CharField(max_length=20, unique=True, editable=False)
    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group   = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, default='unknown')
    national_id   = models.CharField(max_length=20, blank=True)
    photo         = models.ImageField(upload_to='patients/', blank=True, null=True)
    phone         = models.CharField(max_length=15)
    email         = models.EmailField(blank=True)
    address       = models.TextField(blank=True)
    county        = models.CharField(max_length=100, blank=True)
    emergency_name         = models.CharField(max_length=100)
    emergency_relationship = models.CharField(max_length=50)
    emergency_phone        = models.CharField(max_length=15)
    known_allergies        = models.TextField(blank=True)
    chronic_conditions     = models.TextField(blank=True)
    current_medications    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id()
        super().save(*args, **kwargs)

    def get_full_name(self): return f"{self.first_name} {self.last_name}"
    def get_age(self):
        today = timezone.now().date()
        dob   = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    def __str__(self): return f"{self.patient_id} — {self.get_full_name()}"
    class Meta: ordering = ['-created_at']

class Department(models.Model):
    name      = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Appointment(models.Model):
    OUTCOME_CHOICES = [                        # ← fixed: 4-space indent
        ('treated',       'Treated'),
        ('discharged',    'Discharged'),
        ('admitted',      'Admitted'),
        ('medicine_only', 'Medication Only'),
        ('died',          'Died'),
    ]
    STATUS_CHOICES = [
        ('scheduled',  'Scheduled'),
        ('waiting',    'Waiting'),
        ('consulting', 'Consulting'),
        ('completed',  'Completed'),
        ('cancelled',  'Cancelled'),
        ('no_show',    'No Show'),
    ]
    PRIORITY_CHOICES = [
        ('normal',    'Normal'),
        ('urgent',    'Urgent'),
        ('emergency', 'Emergency'),
    ]
    NEXT_STEP_CHOICES = [
        ('',            'Next step'),
        ('triage',      'Triage'),
        ('doctor',      'Doctor'),
        ('lab',         'Lab'),
        ('reception',   'Reception'),
        ('pharmacy',    'Pharmacy'),
        ('ward',        'Ward'),
        ('cashier',     'Cashier'),
        ('follow_up',   'Follow-up'),
        ('home',        'Home'),
        ('discharged',  'Discharged'),
        ('admitted',    'Admitted'),
        ('nutrition',   'Nutrition'),
        ('physiotherapy','Physiotherapy'),
        ('dental',      'Dental'),
        ('optical',     'Optical'),
    ]

    patient        = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor         = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='appointments')
    department     = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority       = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    reason         = models.TextField(blank=True)
    queue_number   = models.PositiveIntegerField(null=True, blank=True)
    reminder_sent  = models.BooleanField(default=False)
    next_step      = models.CharField(max_length=20, choices=NEXT_STEP_CHOICES, default='', blank=True)
    outcome        = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True, default='')  # ← fixed
    created_at     = models.DateTimeField(auto_now_add=True)
    created_by     = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='created_appointments')

    def save(self, *args, **kwargs):
        if not self.queue_number:
            count = Appointment.objects.filter(
                scheduled_date=self.scheduled_date,
                department=self.department).count()
            self.queue_number = count + 1
        super().save(*args, **kwargs)

    def can_be_managed_by(self, user):           # ← added
        role = getattr(user, 'role', None)
        if role == 'admin':
            return True
        allowed = {
            'receptionist':   ['scheduled', 'waiting', 'cancelled'],
            'nurse':          ['waiting', 'consulting'],
            'doctor':         ['waiting', 'consulting', 'completed'],
            'pharmacist':     ['consulting', 'completed'],
            'cashier':        ['consulting', 'completed'],
            'lab_technician': ['consulting', 'completed'],
        }
        return self.status in allowed.get(role, [])

    def get_next_step_display_label(self):
        return dict(self.NEXT_STEP_CHOICES).get(self.next_step, '—')

    def __str__(self):
        return f"#{self.queue_number} — {self.patient.get_full_name()}"
   
class Meta:
        ordering = ['scheduled_date', 'scheduled_time']

class MortalityRecord(models.Model):
    patient          = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='mortality')
    date_of_death    = models.DateTimeField()
    cause_of_death   = models.TextField()
    attending_doctor = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                          null=True, related_name='mortality_records')
    ward             = models.CharField(max_length=100, blank=True)
    notes            = models.TextField(blank=True)
    recorded_by      = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                          null=True, related_name='recorded_mortalities')
    created_at       = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.patient.get_full_name()} — deceased"
    class Meta: ordering = ['-date_of_death']