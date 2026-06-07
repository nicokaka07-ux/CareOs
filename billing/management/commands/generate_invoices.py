from django.core.management.base import BaseCommand
from django.utils import timezone
from opd.models import Appointment
from billing.models import Invoice, InvoiceItem


class Command(BaseCommand):
    help = 'Generate invoices for completed appointments that have no invoice yet.'

    DEFAULT_CONSULTATION_FEE = 500
    DEFAULT_LAB_FEE = 300
    DEFAULT_PHARMACY_FEE = 150

    def handle(self, *args, **options):
        qs = Appointment.objects.filter(status='completed').filter(invoice__isnull=True)
        count = 0
        for appt in qs.select_related('patient'):
            invoice = Invoice.objects.create(
                patient=appt.patient,
                appointment=appt,
                created_by=getattr(appt, 'created_by', None),
            )

            # Consultation line
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f'Consultation — {appt.department.name if appt.department else "General"}',
                quantity=1,
                unit_price=self.DEFAULT_CONSULTATION_FEE,
            )

            # Lab orders
            consultation = getattr(appt, 'consultation', None)
            if consultation:
                lab_orders = consultation.lab_orders.exclude(status='cancelled')
                if lab_orders.exists():
                    for lab in lab_orders:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=f'Lab: {lab.test_name}',
                            quantity=1,
                            unit_price=self.DEFAULT_LAB_FEE,
                        )

                # Prescriptions
                prescriptions = consultation.prescriptions.exclude(status='cancelled')
                if prescriptions.exists():
                    for rx in prescriptions:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=f'Rx: {rx.medication_name} — {rx.dosage} × {rx.duration}',
                            quantity=rx.quantity or 1,
                            unit_price=self.DEFAULT_PHARMACY_FEE,
                        )

            count += 1
            self.stdout.write(self.style.SUCCESS(f'Invoice {invoice.invoice_number} created for appointment {appt.pk}'))

        self.stdout.write(self.style.SUCCESS(f'Done. {count} invoices generated.'))
