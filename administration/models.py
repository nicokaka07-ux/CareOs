from django.db import models

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create','Created'),('update','Updated'),('delete','Deleted'),
        ('login','Logged In'),('logout','Logged Out'),
        ('dispense','Dispensed Medication'),
        ('payment','Recorded Payment'),('void','Voided Record'),
    ]
    user        = models.ForeignKey('accounts.StaffUser', on_delete=models.SET_NULL,
                                     null=True, related_name='audit_logs')
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name  = models.CharField(max_length=100)
    object_id   = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.action} {self.model_name}"

    class Meta: ordering = ['-timestamp']