from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Patient, Appointment, Department, MortalityRecord
from .forms import PatientRegistrationForm, AppointmentForm
from accounts.decorators import role_required

@login_required
@role_required('receptionist','admin')
def opd_dashboard(request):
    today = timezone.now().date()
    return render(request, 'opd/dashboard.html', {
        'total_patients':     Patient.objects.count(),
        'today_appointments': Appointment.objects.filter(scheduled_date=today).count(),
        'waiting_count':      Appointment.objects.filter(scheduled_date=today, status='waiting').count(),
        'consulting_count':   Appointment.objects.filter(scheduled_date=today, status='consulting').count(),
        'today_schedule':     Appointment.objects.filter(scheduled_date=today).select_related('patient','doctor'),
    })

@login_required
@role_required('receptionist','admin')
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
    query    = request.GET.get('q','')
    patients = Patient.objects.filter(is_active=True)
    if query:
        patients = patients.filter(
            Q(first_name__icontains=query)|Q(last_name__icontains=query)|
            Q(patient_id__icontains=query)|Q(phone__icontains=query))
    return render(request, 'opd/patient_list.html', {'patients':patients,'query':query})

@login_required
def patient_detail(request, pk):
    patient      = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.order_by('-scheduled_date')
    return render(request, 'opd/patient_detail.html', {'patient':patient,'appointments':appointments})

@login_required
@role_required('receptionist','admin')
def book_appointment(request):
    initial = {}
    pid = request.GET.get('patient')
    if pid: initial['patient'] = pid
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
    return render(request, 'opd/book_appointment.html', {'form':form})

@login_required
def queue_board(request):
    today = timezone.now().date()
    return render(request, 'opd/queue_board.html', {
        'waiting':    Appointment.objects.filter(
            scheduled_date=today, status='waiting'
        ).select_related('patient','doctor','department').order_by('queue_number'),
        'consulting': Appointment.objects.filter(
            scheduled_date=today, status='consulting'
        ).select_related('patient','doctor','department').order_by('queue_number'),
        'scheduled':  Appointment.objects.filter(
            scheduled_date=today, status='scheduled'
        ).select_related('patient','doctor','department').order_by('queue_number'),
        'completed':  Appointment.objects.filter(
            scheduled_date=today, status='completed'
        ).select_related('patient','doctor','department').order_by('queue_number'),
        'today': today,
    })

@login_required
def update_appointment_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    new  = request.POST.get('status')
    if new in ['scheduled','waiting','consulting','completed','cancelled']:
        appt.status = new
        appt.save()
        messages.success(request, f'Status updated to: {appt.get_status_display()}')
    return redirect('queue_board')

@login_required
@role_required('doctor','admin')
def mortality_list(request):
    records = MortalityRecord.objects.select_related('patient','attending_doctor','recorded_by')
    return render(request, 'opd/mortality_list.html', {'records':records})

@login_required
@role_required('doctor','admin')
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
            ward=request.POST.get('ward',''),
            notes=request.POST.get('notes',''),
            recorded_by=request.user,
        )
        messages.success(request, f'Mortality record saved for {patient.get_full_name()}.')
        return redirect('mortality_list')
    return render(request, 'opd/record_mortality.html',
                  {'patients': Patient.objects.filter(is_active=True)})