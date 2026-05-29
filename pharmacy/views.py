from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Drug, DispenseRecord
from clinical.models import Prescription
from accounts.decorators import role_required

@login_required
@role_required('pharmacist','admin')
def pharmacy_queue(request):
    today     = timezone.now().date()
    pending   = Prescription.objects.filter(
        status='pending'
    ).select_related('patient','doctor','consultation__appointment')
    dispensed = Prescription.objects.filter(
        status='dispensed',
        dispensed_at__date=today
    ).select_related('patient')
    low_stock = [d for d in Drug.objects.filter(is_active=True) if d.is_low_stock]

    # Also show today's appointments for pharmacy department
    from opd.models import Appointment, Department
    try:
        pharmacy_dept = Department.objects.get(name__icontains='pharmacy')
        pharmacy_appts = Appointment.objects.filter(
            scheduled_date=today,
            department=pharmacy_dept,
            status__in=['scheduled','waiting','consulting','completed']
        ).select_related('patient','doctor')
    except Department.DoesNotExist:
        pharmacy_appts = []

    return render(request, 'pharmacy/queue.html', {
        'pending':         pending,
        'dispensed':       dispensed,
        'low_stock':       low_stock,
        'pharmacy_appts':  pharmacy_appts,
    })

@login_required
@role_required('pharmacist','admin')
def dispense(request, prescription_pk):
    prescription = get_object_or_404(Prescription, pk=prescription_pk, status='pending')
    if request.method == 'POST':
        drug = get_object_or_404(Drug, pk=request.POST.get('drug'))
        qty  = prescription.quantity
        if drug.stock_quantity < qty:
            messages.error(request, f'Insufficient stock. Only {drug.stock_quantity} {drug.unit}(s) available.')
            return redirect('pharmacy_queue')
        drug.stock_quantity -= qty
        drug.save()
        DispenseRecord.objects.create(
            prescription=prescription, drug=drug,
            pharmacist=request.user, quantity_dispensed=qty)
        prescription.status       = 'dispensed'
        prescription.dispensed_at = timezone.now()
        prescription.save()
        messages.success(request, f'Dispensed {drug.name} x{qty} successfully.')
        return redirect('pharmacy_queue')
    matching  = Drug.objects.filter(is_active=True, stock_quantity__gt=0,
                    name__icontains=prescription.medication_name.split()[0])
    all_drugs = Drug.objects.filter(is_active=True, stock_quantity__gt=0)
    return render(request, 'pharmacy/dispense.html', {
        'prescription':prescription,'matching_drugs':matching,'all_drugs':all_drugs})

@login_required
@role_required('pharmacist','admin')
def drug_inventory(request):
    query = request.GET.get('q','')
    drugs = Drug.objects.filter(is_active=True)
    if query:
        drugs = drugs.filter(Q(name__icontains=query)|Q(generic_name__icontains=query))
    return render(request, 'pharmacy/inventory.html', {'drugs':drugs,'query':query})

@login_required
@role_required('pharmacist', 'admin')
def add_drug(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if Drug.objects.filter(name__iexact=name).exists():
            messages.error(request, f'"{name}" already exists in inventory. Use Restock to add more stock.')
            return render(request, 'pharmacy/add_drug.html', {'categories': Drug.CATEGORY_CHOICES})
        Drug.objects.create(
            name=name,
            generic_name=request.POST.get('generic_name', ''),
            category=request.POST.get('category'),
            unit=request.POST.get('unit'),
            buying_price=request.POST.get('buying_price'),
            selling_price=request.POST.get('selling_price'),
            stock_quantity=request.POST.get('stock_quantity'),
            minimum_stock=request.POST.get('minimum_stock'),
            expiry_date=request.POST.get('expiry_date') or None,
        )
        messages.success(request, f'{name} added to inventory.')
        return redirect('drug_inventory')
    return render(request, 'pharmacy/add_drug.html', {'categories': Drug.CATEGORY_CHOICES})

@login_required
@role_required('pharmacist','admin')
def restock_drug(request, drug_pk):
    drug = get_object_or_404(Drug, pk=drug_pk)
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 0))
        if qty > 0:
            drug.stock_quantity += qty
            drug.save()
            messages.success(request, f'Restocked {drug.name} by {qty}. New stock: {drug.stock_quantity}')
        return redirect('drug_inventory')
    return render(request, 'pharmacy/restock.html', {'drug':drug})