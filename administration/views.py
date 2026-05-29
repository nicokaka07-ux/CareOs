from django.shortcuts import render, redirect, get_object_or_404  # add redirect & get_object_or_404
from django.contrib import messages                                  # add this
from accounts.forms import StaffCreationForm, StaffPasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from accounts.decorators import role_required
from accounts.models import StaffUser
from opd.models import Patient, Appointment
from pharmacy.models import Drug, DispenseRecord
from billing.models import Invoice, Payment
from .models import AuditLog

@login_required
@role_required('admin')
def admin_dashboard(request):
    today    = timezone.now().date()
    week_ago = today - timedelta(days=7)
    today_revenue = Payment.objects.filter(paid_at__date=today).aggregate(t=Sum('amount'))['t'] or 0
    week_revenue  = Payment.objects.filter(paid_at__date__gte=week_ago).aggregate(t=Sum('amount'))['t'] or 0
    unpaid_total  = sum(float(i.balance) for i in Invoice.objects.filter(status__in=['unpaid','partial']))
    dept_data     = Appointment.objects.filter(scheduled_date__gte=week_ago).values('department__name').annotate(count=Count('id')).order_by('-count')[:8]
    revenue_labels, revenue_values = [], []
    for i in range(6,-1,-1):
        day = today - timedelta(days=i)
        t   = Payment.objects.filter(paid_at__date=day).aggregate(s=Sum('amount'))['s'] or 0
        revenue_labels.append(day.strftime('%a %d'))
        revenue_values.append(float(t))
    top_drugs     = DispenseRecord.objects.values('drug__name').annotate(total=Sum('quantity_dispensed')).order_by('-total')[:5]
    staff_by_role = StaffUser.objects.values('role').annotate(count=Count('id'))
    return render(request, 'administration/dashboard.html', {
        'total_patients':     Patient.objects.count(),
        'new_this_week':      Patient.objects.filter(created_at__date__gte=week_ago).count(),
        'today_appointments': Appointment.objects.filter(scheduled_date=today).count(),
        'today_revenue':      today_revenue,
        'week_revenue':       week_revenue,
        'unpaid_total':       unpaid_total,
        'dept_labels':        [d['department__name'] or 'Unassigned' for d in dept_data],
        'dept_counts':        [d['count'] for d in dept_data],
        'revenue_labels':     revenue_labels,
        'revenue_values':     revenue_values,
        'top_drugs':          top_drugs,
        'role_labels':        [s['role'].title() for s in staff_by_role],
        'role_counts':        [s['count'] for s in staff_by_role],
        'low_stock_drugs':    [d for d in Drug.objects.filter(is_active=True) if d.is_low_stock],
        'expiring_drugs':     [d for d in Drug.objects.filter(is_active=True) if d.is_expiring_soon],
        'recent_logs':        AuditLog.objects.select_related('user').order_by('-timestamp')[:15],
        'today':              today,
    })

@login_required
@role_required('admin')
def audit_log_list(request):
    return render(request, 'administration/audit_logs.html',
                  {'logs': AuditLog.objects.select_related('user').order_by('-timestamp')[:200]})

@login_required
@role_required('admin')
def staff_list(request):
    return render(request, 'administration/staff_list.html',
                  {'staff': StaffUser.objects.all().order_by('role','first_name')})
@login_required
@role_required('admin')
def create_staff(request):
    form = StaffCreationForm()
    if request.method == 'POST':
        form = StaffCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Staff account created for {user.get_full_name()}.')
            return redirect('staff_list')
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'administration/create_staff.html', {'form': form})


@login_required
@role_required('admin')
def reset_staff_password(request, pk):
    staff = get_object_or_404(StaffUser, pk=pk)
    form  = StaffPasswordChangeForm(user=staff)
    if request.method == 'POST':
        form = StaffPasswordChangeForm(user=staff, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Password reset for {staff.get_full_name()}.')
            return redirect('staff_list')
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'administration/reset_password.html', {'form': form, 'staff': staff})
@login_required
@role_required('admin')
def toggle_staff_status(request, pk):
    staff = get_object_or_404(StaffUser, pk=pk)
    if staff == request.user:
        messages.error(request, "You can't deactivate your own account.")
        return redirect('staff_list')
    staff.is_active = not staff.is_active
    staff.save(update_fields=['is_active'])
    status = 'activated' if staff.is_active else 'deactivated'
    messages.success(request, f'{staff.get_full_name()} has been {status}.')
    return redirect('staff_list')