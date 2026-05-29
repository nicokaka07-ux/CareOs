from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StaffUser
from billing.models import Invoice
from opd.models import Patient


class BillingDashboardAccessTests(TestCase):
    def setUp(self):
        self.cashier = StaffUser.objects.create_user(
            username='cashier1',
            password='testpass123',
            role='cashier',
            first_name='Ada',
            last_name='Cashier',
        )
        self.patient = Patient.objects.create(
            first_name='Jane',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='female',
            phone='0712345678',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0798765432',
        )

    def test_dashboard_displays_unpaid_invoices_created_earlier(self):
        invoice = Invoice.objects.create(
            patient=self.patient,
            consultation_fee=1500,
            status='unpaid',
            created_by=self.cashier,
        )
        invoice.created_at = timezone.now() - timedelta(days=3)
        invoice.save(update_fields=['created_at'])

        self.client.force_login(self.cashier)

        response = self.client.get(reverse('billing_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, invoice.invoice_number)
        self.assertContains(response, 'Unpaid Invoices')

    def test_dashboard_displays_paid_invoices_created_earlier(self):
        invoice = Invoice.objects.create(
            patient=self.patient,
            consultation_fee=1500,
            status='paid',
            created_by=self.cashier,
        )
        invoice.created_at = timezone.now() - timedelta(days=5)
        invoice.save(update_fields=['created_at'])

        self.client.force_login(self.cashier)

        response = self.client.get(reverse('billing_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, invoice.invoice_number)
        self.assertContains(response, 'All Invoices')
