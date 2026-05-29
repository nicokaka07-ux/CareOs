from django.contrib.auth.models import AbstractUser
from django.db import models

class StaffUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin',            'System Admin'),
        ('receptionist',     'Receptionist'),
        ('nurse',            'Nurse'),
        # Doctors
        ('doctor',           'General Practitioner'),
        ('surgeon',          'General Surgeon'),
        ('physician',        'Physician / Internist'),
        ('pediatrician',     'Pediatrician'),
        ('gynecologist',     'Gynecologist / Obstetrician'),
        ('cardiologist',     'Cardiologist'),
        ('neurologist',      'Neurologist'),
        ('neurosurgeon',     'Neurosurgeon'),
        ('orthopedic',       'Orthopedic Surgeon'),
        ('dermatologist',    'Dermatologist'),
        ('psychiatrist',     'Psychiatrist'),
        ('radiologist',      'Radiologist'),
        ('anesthesiologist', 'Anesthesiologist'),
        ('urologist',        'Urologist'),
        ('oncologist',       'Oncologist'),
        ('ent',              'ENT Specialist'),
        ('ophthalmologist',  'Ophthalmologist (Eye)'),
        ('dentist',          'Dentist'),
        ('physiotherapist',  'Physiotherapist'),
        # Support
        ('lab_technician',   'Lab Technician'),
        ('pharmacist',       'Pharmacist'),
        ('cashier',          'Cashier'),
        ('nutritionist',     'Nutritionist / Dietitian'),
    ]                                                        # ← was at 0 spaces, now 4
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='receptionist')
    phone         = models.CharField(max_length=15, blank=True)
    department    = models.CharField(max_length=100, blank=True)
    profile_photo = models.ImageField(upload_to='staff/', blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name()} — {self.get_role_display()}"

    @property
    def is_doctor(self): return self.role == 'doctor'
    @property
    def is_nurse(self): return self.role == 'nurse'
    @property
    def is_receptionist(self): return self.role == 'receptionist'
    @property
    def is_pharmacist(self): return self.role == 'pharmacist'
    @property
    def is_cashier(self): return self.role == 'cashier'
    @property
    def is_system_admin(self): return self.role == 'admin'