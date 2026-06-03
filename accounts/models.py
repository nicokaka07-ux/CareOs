from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import random
import string

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


class OTPCode(models.Model):
    """One-Time Password for two-factor authentication during login."""
    user = models.OneToOneField(StaffUser, on_delete=models.CASCADE, related_name='otp_code')
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)

    def __str__(self):
        return f"OTP for {self.user.username}"

    def is_valid(self):
        """Check if OTP is still valid (not expired and attempts not exceeded)."""
        return (
            timezone.now() <= self.expires_at 
            and self.attempts < self.max_attempts
        )

    def is_expired(self):
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at

    def increment_attempts(self):
        """Increment the failed attempt counter."""
        self.attempts += 1
        self.save(update_fields=['attempts'])

    @classmethod
    def generate_otp(cls, user):
        """Generate and save a new OTP for the user."""
        # Delete existing OTP if any
        cls.objects.filter(user=user).delete()
        
        # Generate a 6-digit OTP
        code = ''.join(random.choices(string.digits, k=6))
        
        # Create new OTP valid for 5 minutes
        otp = cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Send OTP via email
        otp.send_email()
        
        return otp
    
    def send_email(self):
        """Send OTP code via email to the configured email address."""
        recipient = self.user.email.strip() if self.user.email else settings.OTP_FALLBACK_EMAIL
        try:
            subject = 'CareOS Login - One-Time Password (OTP)'
            message = f"""
Hello {self.user.get_full_name() or self.user.username},

Your One-Time Password (OTP) for CareOS login is:

{self.code}

This code will expire in 5 minutes. If you did not request this code, please ignore this email.

Do not share this code with anyone.

Best regards,
CareOS Hospital Management System
"""
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't fail the OTP generation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send OTP email: {str(e)}")