from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import TriageRecord, Consultation, LabOrder, Prescription
from .forms import TriageForm, ConsultationForm, LabOrderForm, PrescriptionForm
from opd.models import Appointment, Patient
from accounts.decorators import role_required

@login_required
@role_required('nurse','admin')
def triage_list(request):
    today   = timezone.now().date()
    pending = Appointment.objects.filter(
        scheduled_date=today, status__in=['waiting','scheduled']
    ).select_related('patient','doctor').exclude(triage__isnull=False)
    triaged = Appointment.objects.filter(
        scheduled_date=today
    ).select_related('patient').filter(triage__isnull=False)
    return render(request, 'clinical/triage_list.html', {'pending':pending,'triaged':triaged})

@login_required
@role_required('nurse','admin')
def record_triage(request, appointment_pk):
    appointment = get_object_or_404(Appointment, pk=appointment_pk)
    if hasattr(appointment, 'triage'):
        messages.warning(request, 'Triage already recorded.')
        return redirect('triage_list')
    if request.method == 'POST':
        form = TriageForm(request.POST)
        if form.is_valid():
            triage             = form.save(commit=False)
            triage.appointment = appointment
            triage.patient     = appointment.patient
            triage.nurse       = request.user
            triage.save()
            appointment.status = 'waiting'
            appointment.save()
            messages.success(request, f'Triage recorded for {appointment.patient.get_full_name()}.')
            return redirect('triage_list')
    else:
        form = TriageForm()
    return render(request, 'clinical/record_triage.html', {'form':form,'appointment':appointment})

@login_required
@role_required('doctor','admin')
def emr_dashboard(request):
    today = timezone.now().date()
    return render(request, 'clinical/emr_dashboard.html', {
        'my_appointments': Appointment.objects.filter(
            scheduled_date=today, doctor=request.user,
            status__in=['waiting','consulting']
        ).select_related('patient').order_by('queue_number'),
        'today': today,
    })

@login_required
@role_required('doctor','admin')
def patient_emr(request, appointment_pk):
    appointment  = get_object_or_404(Appointment, pk=appointment_pk)
    patient      = appointment.patient
    consultation = getattr(appointment, 'consultation', None)
    return render(request, 'clinical/patient_emr.html', {
        'appointment':        appointment,
        'patient':            patient,
        'triage':             getattr(appointment, 'triage', None),
        'consultation':       consultation,
        'past_consultations': patient.consultations.exclude(appointment=appointment).order_by('-created_at'),
        'past_labs':          patient.lab_orders.order_by('-ordered_at')[:10],
        'past_prescriptions': patient.prescriptions.order_by('-prescribed_at')[:10],
        'consultation_form':  ConsultationForm(instance=consultation),
        'lab_form':           LabOrderForm(),
        'prescription_form':  PrescriptionForm(),
    })

@login_required
@role_required('doctor','admin')
def save_consultation(request, appointment_pk):
    appointment  = get_object_or_404(Appointment, pk=appointment_pk)
    consultation = getattr(appointment, 'consultation', None)
    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            c             = form.save(commit=False)
            c.appointment = appointment
            c.patient     = appointment.patient
            c.doctor      = request.user
            c.save()
            appointment.status = 'consulting'
            appointment.save()
            messages.success(request, 'Consultation notes saved.')
        else:
            messages.error(request, 'Error saving consultation.')
    return redirect('patient_emr', appointment_pk=appointment_pk)

@login_required
@role_required('doctor','admin')
def add_lab_order(request, appointment_pk):
    appointment  = get_object_or_404(Appointment, pk=appointment_pk)
    consultation = get_object_or_404(Consultation, appointment=appointment)
    if request.method == 'POST':
        form = LabOrderForm(request.POST)
        if form.is_valid():
            lab              = form.save(commit=False)
            lab.consultation = consultation
            lab.patient      = appointment.patient
            lab.doctor       = request.user
            lab.save()
            messages.success(request, f'Lab order added: {lab.test_name}')
    return redirect('patient_emr', appointment_pk=appointment_pk)

@login_required
@role_required('doctor','admin')
def add_prescription(request, appointment_pk):
    appointment  = get_object_or_404(Appointment, pk=appointment_pk)
    consultation = get_object_or_404(Consultation, appointment=appointment)
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            rx              = form.save(commit=False)
            rx.consultation = consultation
            rx.patient      = appointment.patient
            rx.doctor       = request.user
            rx.save()
            messages.success(request, f'Prescription added: {rx.medication_name}')
    return redirect('patient_emr', appointment_pk=appointment_pk)

@login_required
@role_required('doctor','admin')
def complete_consultation(request, appointment_pk):
    appointment        = get_object_or_404(Appointment, pk=appointment_pk)
    appointment.status = 'completed'
    appointment.save()
    messages.success(request, 'Consultation marked as complete.')
    return redirect('emr_dashboard')