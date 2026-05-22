from django.contrib import admin
from .models import TriageRecord, Consultation, LabOrder, Prescription
admin.site.register(TriageRecord)
admin.site.register(Consultation)
admin.site.register(LabOrder)
admin.site.register(Prescription)