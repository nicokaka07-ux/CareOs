from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import StaffUser
from clinical.models import Consultation, Prescription
from opd.models import Appointment, Department, MortalityRecord, Patient


class PatientListVisibilityTests(TestCase):
    def setUp(self):
        self.receptionist = StaffUser.objects.create_user(
            username='receptionist1',
            password='testpass123',
            role='receptionist',
            first_name='Rae',
            last_name='Reception',
        )
        self.department = Department.objects.create(name='General Clinic')
        self.visited_patient = Patient.objects.create(
            first_name='Jane',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='female',
            phone='0712345678',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0798765432',
        )
        self.new_patient = Patient.objects.create(
            first_name='Alex',
            last_name='Smith',
            date_of_birth='1995-04-04',
            gender='male',
            phone='0723456789',
            emergency_name='Emergency Contact',
            emergency_relationship='Parent',
            emergency_phone='0787654321',
        )
        Appointment.objects.create(
            patient=self.visited_patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 20),
            scheduled_time='09:00:00',
            status='completed',
            reason='Follow-up visit',
        )

    def test_patient_list_shows_only_patients_with_visits_and_adds_visit_metadata(self):
        self.client.force_login(self.receptionist)

        response = self.client.get(reverse('patient_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visited_patient.get_full_name())
        self.assertNotContains(response, self.new_patient.get_full_name())
        self.assertContains(response, 'Last visit')
        self.assertContains(response, 'Visits')

    def test_patient_list_can_filter_by_name_and_visit_date(self):
        self.client.force_login(self.receptionist)

        response = self.client.get(reverse('patient_list'), {'q': 'Jane', 'visit_date': '2026-05-20'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visited_patient.get_full_name())
        self.assertNotContains(response, self.new_patient.get_full_name())

    def test_patient_list_excludes_patients_when_visit_date_does_not_match(self):
        self.client.force_login(self.receptionist)

        response = self.client.get(reverse('patient_list'), {'q': 'Jane', 'visit_date': '2026-05-21'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.visited_patient.get_full_name())

    def test_receptionist_can_override_outcome_for_scheduled_visit(self):
        patient = Patient.objects.create(
            first_name='Manual',
            last_name='Outcome',
            date_of_birth='2001-01-01',
            gender='female',
            phone='0778901234',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0789012345',
        )
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 26),
            scheduled_time='09:00:00',
            status='scheduled',
            reason='Routine review',
        )

        self.client.force_login(self.receptionist)
        response = self.client.post(
            reverse('update_appointment_outcome', args=[appointment.pk]),
            {'outcome': 'discharged'},
        )

        self.assertRedirects(response, reverse('patient_list'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.outcome, 'discharged')

        response = self.client.get(reverse('patient_list'))
        self.assertContains(response, 'Discharged')
        self.assertContains(response, patient.get_full_name())

    def test_receptionist_can_clear_manual_outcome(self):
        patient = Patient.objects.create(
            first_name='Clear',
            last_name='Override',
            date_of_birth='1999-09-09',
            gender='male',
            phone='0789012356',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0790123467',
        )
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 27),
            scheduled_time='09:30:00',
            status='scheduled',
            reason='Follow-up review',
            outcome='discharged',
        )

        self.client.force_login(self.receptionist)
        response = self.client.post(
            reverse('update_appointment_outcome', args=[appointment.pk]),
            {'outcome': ''},
        )

        self.assertRedirects(response, reverse('patient_list'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.outcome, '')

    def test_doctor_can_mark_consulting_visit_done_and_set_next_step(self):
        doctor = StaffUser.objects.create_user(
            username='doctor_clinic',
            password='testpass123',
            role='doctor',
            first_name='Doc',
            last_name='Clinic',
            department='General Clinic',
        )
        patient = Patient.objects.create(
            first_name='Consult',
            last_name='Patient',
            date_of_birth='1994-04-04',
            gender='male',
            phone='0791234567',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0712345678',
        )
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            department=self.department,
            scheduled_date=date(2026, 5, 28),
            scheduled_time='09:00:00',
            status='consulting',
            reason='Follow-up consultation',
        )

        self.client.force_login(doctor)
        response = self.client.post(
            reverse('update_appointment_status', args=[appointment.pk]),
            {'status': 'completed', 'next_step': 'pharmacy', 'next': reverse('patient_detail', args=[patient.pk])},
        )

        self.assertRedirects(response, reverse('patient_detail', args=[patient.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')
        self.assertEqual(appointment.next_step, 'pharmacy')

        detail_response = self.client.get(reverse('patient_detail', args=[patient.pk]))
        self.assertContains(detail_response, 'Pharmacy')
        self.assertContains(detail_response, 'Next step')

    def test_only_matching_department_can_change_status(self):
        lab_staff = StaffUser.objects.create_user(
            username='lab_staff',
            password='testpass123',
            role='nurse',
            first_name='Lab',
            last_name='Staff',
            department='Laboratory',
        )
        patient = Patient.objects.create(
            first_name='Restricted',
            last_name='Patient',
            date_of_birth='1988-08-08',
            gender='female',
            phone='0702345679',
            emergency_name='Emergency Contact',
            emergency_relationship='Parent',
            emergency_phone='0723456780',
        )
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 29),
            scheduled_time='10:00:00',
            status='scheduled',
            reason='Routine review',
        )

        self.client.force_login(lab_staff)
        response = self.client.post(
            reverse('update_appointment_status', args=[appointment.pk]),
            {'status': 'waiting', 'next': reverse('opd_dashboard')},
        )

        self.assertEqual(response.status_code, 403)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'scheduled')

    def test_dashboard_summary_cards_link_to_filtered_patient_lists(self):
        self.client.force_login(self.receptionist)

        response = self.client.get(reverse('opd_dashboard'))

        self.assertContains(response, f'href="{reverse("patient_list")}"')
        self.assertContains(response, f'href="{reverse("patient_list")}?appointment_status=today"')
        self.assertContains(response, f'href="{reverse("patient_list")}?appointment_status=waiting"')
        self.assertContains(response, f'href="{reverse("patient_list")}?appointment_status=consulting"')

    def test_patient_list_filters_patients_by_appointment_status(self):
        waiting_patient = Patient.objects.create(
            first_name='Waiting',
            last_name='Patient',
            date_of_birth='1993-03-03',
            gender='male',
            phone='0790123478',
            emergency_name='Emergency Contact',
            emergency_relationship='Parent',
            emergency_phone='0701234589',
        )
        consulting_patient = Patient.objects.create(
            first_name='Consulting',
            last_name='Patient',
            date_of_birth='1997-07-07',
            gender='female',
            phone='0711234590',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0722345601',
        )
        Appointment.objects.create(
            patient=waiting_patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 21),
            scheduled_time='10:00:00',
            status='waiting',
            reason='Waiting room follow-up',
        )
        Appointment.objects.create(
            patient=consulting_patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 22),
            scheduled_time='11:00:00',
            status='consulting',
            reason='Consultation in progress',
        )

        self.client.force_login(self.receptionist)

        waiting_response = self.client.get(reverse('patient_list'), {'appointment_status': 'waiting'})
        consulting_response = self.client.get(reverse('patient_list'), {'appointment_status': 'consulting'})

        self.assertContains(waiting_response, waiting_patient.get_full_name())
        self.assertNotContains(waiting_response, consulting_patient.get_full_name())
        self.assertContains(consulting_response, consulting_patient.get_full_name())
        self.assertNotContains(consulting_response, waiting_patient.get_full_name())

    def test_patient_list_displays_outcome_badges_for_visit_statuses(self):
        doctor = StaffUser.objects.create_user(
            username='doctor_outcome',
            password='testpass123',
            role='doctor',
            first_name='Doc',
            last_name='Outcome',
        )

        treated_patient = Patient.objects.create(
            first_name='Treated',
            last_name='Patient',
            date_of_birth='1992-02-02',
            gender='male',
            phone='0734567890',
            emergency_name='Emergency Contact',
            emergency_relationship='Spouse',
            emergency_phone='0711122233',
        )
        treated_appointment = Appointment.objects.create(
            patient=treated_patient,
            doctor=doctor,
            department=self.department,
            scheduled_date=date(2026, 5, 22),
            scheduled_time='10:00:00',
            status='completed',
            reason='Follow-up',
        )
        Consultation.objects.create(
            appointment=treated_appointment,
            patient=treated_patient,
            doctor=doctor,
            presenting_complaint='Headache',
            diagnosis='Migraine',
            treatment_plan='Rest and analgesics',
        )

        medicine_patient = Patient.objects.create(
            first_name='Medication',
            last_name='Only',
            date_of_birth='1988-08-08',
            gender='female',
            phone='0745678901',
            emergency_name='Emergency Contact',
            emergency_relationship='Parent',
            emergency_phone='0722233344',
        )
        medicine_appointment = Appointment.objects.create(
            patient=medicine_patient,
            doctor=doctor,
            department=self.department,
            scheduled_date=date(2026, 5, 23),
            scheduled_time='11:00:00',
            status='completed',
            reason='Prescription only',
        )
        medicine_consultation = Consultation.objects.create(
            appointment=medicine_appointment,
            patient=medicine_patient,
            doctor=doctor,
            presenting_complaint='Cold symptoms',
            diagnosis='',
            treatment_plan='',
        )
        Prescription.objects.create(
            consultation=medicine_consultation,
            patient=medicine_patient,
            doctor=doctor,
            medication_name='Paracetamol',
            dosage='500mg',
            frequency='every 6 hours',
            duration='3 days',
        )

        discharged_patient = Patient.objects.create(
            first_name='Discharged',
            last_name='Patient',
            date_of_birth='1995-05-05',
            gender='male',
            phone='0756789012',
            emergency_name='Emergency Contact',
            emergency_relationship='Sibling',
            emergency_phone='0733344455',
        )
        Appointment.objects.create(
            patient=discharged_patient,
            doctor=None,
            department=self.department,
            scheduled_date=date(2026, 5, 24),
            scheduled_time='12:00:00',
            status='completed',
            reason='Routine review',
        )

        died_patient = Patient.objects.create(
            first_name='Died',
            last_name='Patient',
            date_of_birth='1977-07-07',
            gender='female',
            phone='0767890123',
            emergency_name='Emergency Contact',
            emergency_relationship='Daughter',
            emergency_phone='0744455566',
            is_active=False,
        )
        died_appointment = Appointment.objects.create(
            patient=died_patient,
            doctor=doctor,
            department=self.department,
            scheduled_date=date(2026, 5, 25),
            scheduled_time='13:00:00',
            status='completed',
            reason='Final review',
        )
        MortalityRecord.objects.create(
            patient=died_patient,
            date_of_death='2026-05-25T15:00:00Z',
            cause_of_death='Complications from pneumonia',
            attending_doctor=doctor,
            ward='General Ward',
        )

        self.client.force_login(self.receptionist)
        response = self.client.get(reverse('patient_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Treated')
        self.assertContains(response, 'Medication only')
        self.assertContains(response, 'Discharged')
        self.assertContains(response, 'Died')
