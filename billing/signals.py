from django.db.models.signals import post_save
from django.dispatch import receiver

from opd.models import Appointment
from billing.models import Invoice, InvoiceItem


@receiver(post_save, sender=Appointment)
def generate_invoice(sender, instance, created, **kwargs):

    if getattr(instance, 'status', None) != 'completed':
        return

    invoice, created = Invoice.objects.get_or_create(
        appointment=instance,
        defaults={
            'patient': instance.patient,
        }
    )

    if created:
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Consultation Fee',
            quantity=1,
            unit_price=1000
        )
