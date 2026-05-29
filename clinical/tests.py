from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StaffUser
from opd.models import Appointment, Department, Patient


class ClinicalDashboardTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='General Clinic')
        self.current_doctor = StaffUser.objects.create_user(
            username='doctor_a',
            password='testpass123',
            role='doctor',
            first_name='Ada',
            last_name='Doctor',
        )
        self.other_doctor = StaffUser.objects.create_user(
            username='doctor_b',
            password='testpass123',
            role='doctor',
            first_name='Ben',
            last_name='Doctor',
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

    def test_emr_dashboard_shows_patients_assigned_to_other_doctors_and_completed(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.other_doctor,
            department=self.department,
            scheduled_date=timezone.now().date(),
            scheduled_time='09:00:00',
            status='completed',
            reason='Follow-up consultation',
        )

        self.client.force_login(self.current_doctor)

        response = self.client.get(reverse('emr_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.get_full_name())
        self.assertContains(response, 'Completed')
