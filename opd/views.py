from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Max, Q
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Patient, Appointment, Department, MortalityRecord
from .forms import PatientRegistrationForm, AppointmentForm
from accounts.decorators import role_required


OUTCOME_BADGE_CLASSES = {
    'treated':      'success',
    'discharged':   'secondary',
    'admitted':     'warning',
    'medicine_only':'info',
    'died':         'danger',
}

# Free-text outcomes written by update_next_step → badge colour
_FREE_TEXT_OUTCOME_CLASSES = {
    'referred to pharmacy':              'info',
    'referred to lab':                   'primary',
    'referred to ward':                  'warning',
    'referred to dental':                'secondary',
    'referred to optical':               'secondary',
    'referred to physiotherapy':         'secondary',
    'referred to nutrition':             'secondary',
    'sent to billing & cashier':         'warning',
    'sent to cashier/billing before discharge': 'warning',
    'admitted to ward':                  'warning',
    'returning to doctor':               'primary',
    'discharged home':                   'secondary',
    'follow-up appointment required':    'info',
}


def _get_latest_appointment(patient):
    appointments = list(patient.appointments.all())
    if not appointments:
        return None
    return sorted(
        appointments,
        key=lambda appt: (appt.scheduled_date, appt.scheduled_time, appt.pk),
        reverse=True,
    )[0]


def _get_patient_outcome(patient):
    latest_appointment = _get_latest_appointment(patient)

    if latest_appointment is None:
        return 'No visit', 'secondary'

    try:
        has_mortality = bool(patient.mortality)
    except Exception:
        has_mortality = False

    if has_mortality:
        return 'Died', 'danger'

    if latest_appointment.outcome:
        # outcome may be a choice key ('treated') OR a free-text string
        # ('Referred to Pharmacy') written by update_next_step
        badge = OUTCOME_BADGE_CLASSES.get(latest_appointment.outcome)
        if badge:
            # It's a proper choice key — use get_outcome_display()
            return latest_appointment.get_outcome_display(), badge

        # Fall back to free-text lookup (case-insensitive)
        badge = _FREE_TEXT_OUTCOME_CLASSES.get(
            latest_appointment.outcome.lower(), 'primary'
        )
        return latest_appointment.outcome, badge

    if latest_appointment.status == 'completed':
        consultation = getattr(latest_appointment, 'consultation', None)
        if consultation and consultation.diagnosis and consultation.diagnosis.strip():
            return 'Treated', 'success'

        has_prescriptions = bool(consultation and consultation.prescriptions.exists())
        if has_prescriptions:
            return 'Medication only', 'info'

        department_name = (
            latest_appointment.department.name if latest_appointment.department else ''
        ).lower()
        if any(token in department_name for token in ('admit', 'admission', 'ward', 'inpatient', 'ipd')):
            return 'Admitted', 'warning'

        return 'Discharged', 'secondary'

    if latest_appointment.status == 'cancelled':
        return 'Cancelled', 'dark'

    if latest_appointment.status == 'no_show':
        return 'No show', 'warning'

    return latest_appointment.get_status_display(), 'primary'


def _redirect_after_appointment_action(request, appointment, default_view='patient_detail'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)

    if appointment.patient_id and default_view == 'patient_detail':
        return redirect('patient_detail', pk=appointment.patient_id)
    return redirect('queue_board')


@login_required
@role_required('receptionist', 'admin')
def opd_dashboard(request):
    today = timezone.now().date()
    return render(request, 'opd/dashboard.html', {
        'total_patients':     Patient.objects.count(),
        'today_appointments': Appointment.objects.filter(scheduled_date=today).count(),
        'waiting_count':      Appointment.objects.filter(scheduled_date=today, status='waiting').count(),
        'consulting_count':   Appointment.objects.filter(scheduled_date=today, status='consulting').count(),
        'today_schedule':     Appointment.objects.filter(scheduled_date=today).select_related('patient', 'doctor'),
    })


@login_required
@role_required('receptionist', 'admin')
def register_patient(request):
    form = PatientRegistrationForm()
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient registered! ID: {patient.patient_id}')
            return redirect('patient_detail', pk=patient.pk)
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'opd/register_patient.html', {'form': form})


@login_required
def patient_list(request):
    query              = request.GET.get('q', '')
    visit_date         = request.GET.get('visit_date', '')
    appointment_status = request.GET.get('appointment_status', 'all')
    today              = timezone.now().date()

    patients = Patient.objects.filter(
        Q(is_active=True) | Q(mortality__isnull=False),
        appointments__isnull=False,
    )
    patients = patients.annotate(
        visit_count=Count('appointments', distinct=True),
        last_visit_date=Max('appointments__scheduled_date'),
    ).filter(last_visit_date__isnull=False).order_by('-last_visit_date')

    if appointment_status == 'today':
        patients = patients.filter(appointments__scheduled_date=today)
    elif appointment_status in ['waiting', 'consulting']:
        patients = patients.filter(appointments__status=appointment_status)

    if query:
        patients = patients.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) |
            Q(patient_id__icontains=query) | Q(phone__icontains=query)
        )
    if visit_date:
        patients = patients.filter(appointments__scheduled_date=visit_date)

    patients = patients.prefetch_related(
        'appointments__department',
        'appointments__consultation__prescriptions',
    ).distinct()

    for patient in patients:
        patient.outcome_label, patient.outcome_class = _get_patient_outcome(patient)

    return render(request, 'opd/patient_list.html', {
        'patients':               patients,
        'query':                  query,
        'visit_date':             visit_date,
        'appointment_status':     appointment_status,
        'appointment_status_label': {
            'all':        'All patients',
            'today':      'Today appointments',
            'waiting':    'Waiting room',
            'consulting': 'In consultation',
        }.get(appointment_status, 'All patients'),
    })


@login_required
def patient_detail(request, pk):
    patient      = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.order_by('-scheduled_date')
    return render(request, 'opd/patient_detail.html', {
        'patient':      patient,
        'appointments': appointments,
    })


@login_required
@role_required('receptionist', 'admin')
def book_appointment(request):
    initial = {}
    pid = request.GET.get('patient')
    if pid:
        initial['patient'] = pid
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt            = form.save(commit=False)
            appt.created_by = request.user
            appt.save()
            messages.success(request, f'Appointment booked! Queue #{appt.queue_number}')
            return redirect('queue_board')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = AppointmentForm(initial=initial)
    return render(request, 'opd/book_appointment.html', {'form': form})


@login_required
@role_required('receptionist', 'admin')
def update_appointment_outcome(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    outcome     = request.POST.get('outcome', '')

    valid_outcomes = dict(Appointment.OUTCOME_CHOICES)
    if outcome not in valid_outcomes and outcome != '':
        messages.error(request, 'Please select a valid outcome.')
        return redirect('patient_detail', pk=appointment.patient.pk)

    appointment.outcome = outcome
    appointment.save(update_fields=['outcome'])

    if outcome:
        messages.success(request, f'Outcome updated to {appointment.get_outcome_display()}.')
    else:
        messages.success(request, 'Outcome cleared.')

    return redirect('patient_list')


@login_required
def queue_board(request):
    today = timezone.now().date()
    return render(request, 'opd/queue_board.html', {
        'waiting':   Appointment.objects.filter(
            scheduled_date=today, status='waiting'
        ).select_related('patient', 'doctor', 'department').order_by('queue_number'),
        'consulting': Appointment.objects.filter(
            scheduled_date=today, status='consulting'
        ).select_related('patient', 'doctor', 'department').order_by('queue_number'),
        'scheduled':  Appointment.objects.filter(
            scheduled_date=today, status='scheduled'
        ).select_related('patient', 'doctor', 'department').order_by('queue_number'),
        'completed':  Appointment.objects.filter(
            scheduled_date=today, status='completed'
        ).select_related('patient', 'doctor', 'department').order_by('queue_number'),
        'today': today,
    })


@login_required
def update_appointment_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)

    if not appt.can_be_managed_by(request.user):
        return render(request, '403.html', status=403)

    new       = request.POST.get('status')
    next_step = request.POST.get('next_step', '')

    valid_statuses   = ['scheduled', 'waiting', 'consulting', 'completed', 'cancelled']
    valid_next_steps = dict(Appointment.NEXT_STEP_CHOICES)

    if new not in valid_statuses:
        messages.error(request, 'Please select a valid status.')
        return _redirect_after_appointment_action(request, appt)

    if next_step not in valid_next_steps:
        messages.error(request, 'Please select a valid next step.')
        return _redirect_after_appointment_action(request, appt)

    appt.status    = new
    appt.next_step = next_step
    appt.save(update_fields=['status', 'next_step'])

    messages.success(request, f'Status updated to: {appt.get_status_display()}')
    if next_step:
        messages.info(request, f'Next step marked as {appt.get_next_step_display()}.')

    return _redirect_after_appointment_action(request, appt)


@login_required
@role_required('doctor', 'admin')
def mortality_list(request):
    records = MortalityRecord.objects.select_related('patient', 'attending_doctor', 'recorded_by')
    return render(request, 'opd/mortality_list.html', {'records': records})


@login_required
@role_required('doctor', 'admin')
def record_mortality(request):
    if request.method == 'POST':
        patient           = get_object_or_404(Patient, pk=request.POST.get('patient'))
        patient.is_active = False
        patient.save()
        MortalityRecord.objects.create(
            patient=patient,
            date_of_death=request.POST.get('date_of_death'),
            cause_of_death=request.POST.get('cause_of_death'),
            attending_doctor=request.user,
            ward=request.POST.get('ward', ''),
            notes=request.POST.get('notes', ''),
            recorded_by=request.user,
        )
        messages.success(request, f'Mortality record saved for {patient.get_full_name()}.')
        return redirect('mortality_list')
    return render(request, 'opd/record_mortality.html',
                  {'patients': Patient.objects.filter(is_active=True)})


@login_required
def update_next_step(request, pk):
    appt      = get_object_or_404(Appointment, pk=pk)
    next_step = request.POST.get('next_step', '')
    appt.next_step = next_step

    if next_step == 'home':
        appt.next_step = 'cashier'
        appt.outcome   = 'Sent to Cashier/Billing before discharge'
        appt.status    = 'consulting'
        messages.warning(request,
            '⚠️ Patient must go to Billing/Cashier before being discharged home.')
    elif next_step == 'cashier':
        appt.status  = 'consulting'
        appt.outcome = 'Sent to Billing & Cashier'
        messages.success(request, 'Patient sent to Billing & Cashier.')
    elif next_step in ['lab', 'pharmacy', 'ward', 'dental',
                       'optical', 'physiotherapy', 'nutrition']:
        appt.status  = 'consulting'
        appt.outcome = f"Referred to {next_step.title()}"
        messages.success(request, f'Patient referred to {next_step.title()}.')
    elif next_step == 'doctor':
        appt.status  = 'waiting'
        appt.outcome = 'Returning to Doctor'
        messages.success(request, 'Patient returning to Doctor.')
    elif next_step == 'discharged':
        appt.status  = 'completed'
        appt.outcome = 'Discharged Home'
        messages.success(request, 'Patient discharged home.')
    elif next_step == 'follow_up':
        appt.status  = 'completed'
        appt.outcome = 'Follow-up Appointment Required'
        messages.success(request, 'Patient set for follow-up.')
    elif next_step == 'admitted':
        appt.status  = 'consulting'
        appt.outcome = 'Admitted to Ward'
        messages.success(request, 'Patient admitted to ward.')

    appt.save()
    return redirect(request.META.get('HTTP_REFERER', 'queue_board'))