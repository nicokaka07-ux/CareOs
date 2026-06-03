import json
from typing import Any
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Invoice, Payment, MpesaTransaction
from .mpesa import stk_push
from opd.models import Patient, Appointment
from clinical.models import LabOrder, Prescription, Consultation
from accounts.decorators import role_required


def _build_invoice_line_items(invoice):
    """
    Return a structured list of line items grouped by department
    so the template (and print view) can show a full breakdown.
    """
    sections = []

    # ── Consultation ──────────────────────────────────────────────
    if invoice.consultation_fee > 0:
        rows = [{'description': 'Consultation fee', 'amount': invoice.consultation_fee}]
        if invoice.appointment:
            appt = invoice.appointment
            dept = appt.department.name if appt.department else 'General'
            dr   = appt.doctor.get_full_name() if appt.doctor else '—'
            rows[0]['description'] = f'Consultation — {dept} (Dr. {dr})'
        sections.append({'department': 'Consultation', 'icon': '🩺', 'rows': rows,
                         'subtotal': invoice.consultation_fee})

    # ── Lab Orders ────────────────────────────────────────────────
    if invoice.appointment:
        consultation = getattr(invoice.appointment, 'consultation', None)
        if consultation:
            labs = consultation.lab_orders.exclude(status='cancelled')
            if labs.exists():
                lab_rows = []
                for lab in labs:
                    # Each lab order stores its own fee if present; fall back to 0
                    fee = getattr(lab, 'fee', None) or 0
                    lab_rows.append({
                        'description': lab.test_name,
                        'status':      lab.get_status_display(),
                        'amount':      fee,
                    })
                # If no per-item fees, show the invoice-level lab_fee as one line
                if not any(r['amount'] for r in lab_rows):
                    lab_rows = [{'description': f'{len(lab_rows)} test(s) ordered',
                                 'amount': invoice.lab_fee}]
                sections.append({'department': 'Laboratory', 'icon': '🔬',
                                 'rows': lab_rows,
                                 'subtotal': invoice.lab_fee})
            elif invoice.lab_fee > 0:
                sections.append({'department': 'Laboratory', 'icon': '🔬',
                                 'rows': [{'description': 'Laboratory tests', 'amount': invoice.lab_fee}],
                                 'subtotal': invoice.lab_fee})
        elif invoice.lab_fee > 0:
            sections.append({'department': 'Laboratory', 'icon': '🔬',
                             'rows': [{'description': 'Laboratory tests', 'amount': invoice.lab_fee}],
                             'subtotal': invoice.lab_fee})
    elif invoice.lab_fee > 0:
        sections.append({'department': 'Laboratory', 'icon': '🔬',
                         'rows': [{'description': 'Laboratory tests', 'amount': invoice.lab_fee}],
                         'subtotal': invoice.lab_fee})

    # ── Pharmacy / Prescriptions ──────────────────────────────────
    if invoice.appointment:
        consultation = getattr(invoice.appointment, 'consultation', None)
        if consultation:
            rxs = consultation.prescriptions.exclude(status='cancelled')
            if rxs.exists():
                rx_rows = []
                for rx in rxs:
                    fee = getattr(rx, 'fee', None) or 0
                    rx_rows.append({
                        'description': f'{rx.medication_name} — {rx.dosage} × {rx.duration}',
                        'status':      rx.get_status_display(),
                        'amount':      fee,
                    })
                if not any(r['amount'] for r in rx_rows):
                    rx_rows = [{'description': f'{len(rx_rows)} medication(s) prescribed',
                                'amount': invoice.pharmacy_fee}]
                sections.append({'department': 'Pharmacy', 'icon': '💊',
                                 'rows': rx_rows, 'subtotal': invoice.pharmacy_fee})
            elif invoice.pharmacy_fee > 0:
                sections.append({'department': 'Pharmacy', 'icon': '💊',
                                 'rows': [{'description': 'Medications', 'amount': invoice.pharmacy_fee}],
                                 'subtotal': invoice.pharmacy_fee})
        elif invoice.pharmacy_fee > 0:
            sections.append({'department': 'Pharmacy', 'icon': '💊',
                             'rows': [{'description': 'Medications', 'amount': invoice.pharmacy_fee}],
                             'subtotal': invoice.pharmacy_fee})
    elif invoice.pharmacy_fee > 0:
        sections.append({'department': 'Pharmacy', 'icon': '💊',
                         'rows': [{'description': 'Medications', 'amount': invoice.pharmacy_fee}],
                         'subtotal': invoice.pharmacy_fee})

    # ── Other / Miscellaneous ─────────────────────────────────────
    if invoice.other_fee > 0:
        sections.append({'department': 'Other Services', 'icon': '🏥',
                         'rows': [{'description': invoice.notes or 'Miscellaneous charges',
                                   'amount': invoice.other_fee}],
                         'subtotal': invoice.other_fee})

    return sections


@login_required
@role_required('cashier', 'admin')
def billing_dashboard(request):
    today = timezone.now().date()
    
    # Search for specific patient if q parameter is provided
    patient_query = request.GET.get('q', '').strip()
    patient = None
    patient_charges = None
    
    if patient_query:
        from opd.models import Patient
        try:
            # Try to find by patient ID or name
            patient = Patient.objects.filter(
                Q(patient_id__icontains=patient_query) |
                Q(first_name__icontains=patient_query) |
                Q(last_name__icontains=patient_query)
            ).first()
            
            if patient:
                # Get all charges for this patient from all departments
                from django.db.models import Q as DjangoQ
                patient_appointments: Any = getattr(patient, 'appointments')
                appointments = patient_appointments.select_related('consultation')
                
                patient_charges = {
                    'patient': patient,
                    'consultations': [],
                    'labs': [],
                    'prescriptions': [],
                    'today_appointment': None,
                }
                
                # Get today's appointment if any
                today_appt = appointments.filter(scheduled_date=today).first()
                if today_appt:
                    patient_charges['today_appointment'] = today_appt
                    if hasattr(today_appt, 'consultation') and today_appt.consultation:
                        patient_charges['consultations'].append({
                            'appointment': today_appt,
                            'fee': 500  # Default consultation fee - can be configured
                        })
                        # Get lab orders from this consultation
                        patient_charges['labs'].extend(
                            today_appt.consultation.lab_orders.exclude(status='cancelled')
                        )
                        # Get prescriptions from this consultation
                        patient_charges['prescriptions'].extend(
                            today_appt.consultation.prescriptions.exclude(status='cancelled')
                        )
                
                # Calculate totals
                patient_charges['total_labs'] = len(patient_charges['labs'])
                patient_charges['total_prescriptions'] = len(patient_charges['prescriptions'])
                patient_charges['consultation_total'] = sum(c['fee'] for c in patient_charges['consultations']) if patient_charges['consultations'] else 0
                patient_charges['lab_fee_total'] = 300 * patient_charges['total_labs'] if patient_charges['total_labs'] > 0 else 0
                patient_charges['pharmacy_fee_total'] = 150 * patient_charges['total_prescriptions'] if patient_charges['total_prescriptions'] > 0 else 0
                patient_charges['grand_total'] = (
                    patient_charges['consultation_total'] + 
                    patient_charges['lab_fee_total'] + 
                    patient_charges['pharmacy_fee_total']
                )
        except Exception as e:
            messages.warning(request, f'Error searching for patient: {str(e)}')
    
    return render(request, 'billing/dashboard.html', {
        'invoices':        Invoice.objects.filter(created_at__date=today).select_related('patient'),
        'all_invoices':    Invoice.objects.select_related('patient').order_by('-created_at')[:50],
        'unpaid_invoices': Invoice.objects.filter(status='unpaid').select_related('patient').order_by('-created_at')[:20],
        'total_revenue':   Payment.objects.filter(paid_at__date=today).aggregate(t=Sum('amount'))['t'] or 0,
        'unpaid_count':    Invoice.objects.filter(status='unpaid').count(),
        'today':           today,
        'patient_query':   patient_query,
        'patient_charges': patient_charges,
    })


@login_required
@role_required('cashier', 'admin')
def create_invoice(request):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient'))
        appointment_pk = request.POST.get('appointment')
        appointment    = None
        if appointment_pk:
            appointment = Appointment.objects.filter(pk=appointment_pk, patient=patient).first()

        invoice = Invoice.objects.create(
            patient=patient,
            appointment=appointment,
            consultation_fee=request.POST.get('consultation_fee', 0) or 0,
            lab_fee=request.POST.get('lab_fee', 0) or 0,
            pharmacy_fee=request.POST.get('pharmacy_fee', 0) or 0,
            other_fee=request.POST.get('other_fee', 0) or 0,
            discount=request.POST.get('discount', 0) or 0,
            notes=request.POST.get('notes', ''),
            created_by=request.user,
        )
        messages.success(request, f'Invoice {invoice.invoice_number} created.')
        return redirect('invoice_detail', pk=invoice.pk)

    # Pre-fill from appointment if ?appointment=<pk> is passed
    appointment_pk = request.GET.get('appointment')
    appointment    = None
    patient        = None
    if appointment_pk:
        appointment = Appointment.objects.filter(pk=appointment_pk).select_related(
            'patient', 'consultation'
        ).first()
        if appointment:
            patient = appointment.patient

    return render(request, 'billing/create_invoice.html', {
        'patients':    Patient.objects.filter(is_active=True),
        'appointment': appointment,
        'patient':     patient,
    })


@login_required
def invoice_detail(request, pk):
    invoice    = get_object_or_404(Invoice, pk=pk)
    line_items = _build_invoice_line_items(invoice)
    return render(request, 'billing/invoice_detail.html', {
        'invoice':    invoice,
        'payments':   getattr(invoice, 'payments').all(),
        'line_items': line_items,
    })


@login_required
def invoice_print(request, pk):
    """Printer-friendly view — no navbar, clean layout."""
    invoice    = get_object_or_404(Invoice, pk=pk)
    line_items = _build_invoice_line_items(invoice)
    return render(request, 'billing/invoice_print.html', {
        'invoice':    invoice,
        'payments':   getattr(invoice, 'payments').all(),
        'line_items': line_items,
    })


@login_required
@role_required('cashier', 'admin')
def record_payment(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('invoice_detail', pk=invoice.pk)
        Payment.objects.create(
            invoice=invoice,
            method=request.POST.get('method'),
            amount=amount,
            reference=request.POST.get('reference', ''),
            received_by=request.user,
            notes=request.POST.get('notes', ''),
        )
        invoice_payments = getattr(invoice, 'payments')
        total_paid    = sum(p.amount for p in invoice_payments.all())
        invoice.status = 'paid' if total_paid >= invoice.total else 'partial'
        invoice.save()
        messages.success(request, f'Payment of KES {amount:,.2f} recorded.')
        return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'billing/record_payment.html', {'invoice': invoice})


@login_required
@role_required('cashier', 'admin')
def mpesa_stk_push(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        phone  = request.POST.get('phone_number', '').strip()
        amount = request.POST.get('amount', invoice.balance)

        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect('invoice_detail', pk=invoice.pk)

        result = stk_push(phone, float(amount), invoice.invoice_number)

        if result.get('ResponseCode') == '0':
            tx = MpesaTransaction.objects.create(
                invoice=invoice,
                phone_number=phone,
                amount=amount,
                checkout_request_id=result.get('CheckoutRequestID', ''),
                merchant_request_id=result.get('MerchantRequestID', ''),
                status='pending',
            )
            return redirect('mpesa_waiting', checkout_request_id=tx.checkout_request_id)
        else:
            messages.error(request, 'STK push failed. Please try again.')
            return redirect('invoice_detail', pk=invoice.pk)

    return render(request, 'billing/mpesa_stk_push.html', {'invoice': invoice})


@csrf_exempt
def mpesa_callback(request):
    import logging
    logger = logging.getLogger('mpesa')
    
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            logger.info(f"M-Pesa callback received: {json.dumps(data, indent=2)}")
            
            callback    = data.get('Body', {}).get('stkCallback', {})
            checkout_id = callback.get('CheckoutRequestID')
            result_code = callback.get('ResultCode')
            result_desc = callback.get('ResultDesc', '')

            logger.info(f"Processing callback: checkout_id={checkout_id}, result_code={result_code}")

            try:
                tx = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
            except MpesaTransaction.DoesNotExist:
                logger.error(f"Transaction not found for checkout_id: {checkout_id}")
                return JsonResponse({'status': 'not found'})

            if result_code == 0:
                items   = callback.get('CallbackMetadata', {}).get('Item', [])
                receipt = ''
                amount  = 0

                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        receipt = item.get('Value', '')
                    elif item.get('Name') == 'Amount':
                        amount = item.get('Value', 0)

                logger.info(f"Payment successful: receipt={receipt}, amount={amount}")
                tx.status        = 'success'
                tx.mpesa_receipt = receipt
                tx.result_desc   = result_desc
                tx.completed_at  = timezone.now()
                tx.save()
                logger.info(f"Transaction {checkout_id} marked as success")

                Payment.objects.create(
                    invoice=tx.invoice,
                    method='mpesa',
                    amount=tx.amount,
                    reference=receipt,
                    received_by=None,
                    notes=f'M-Pesa STK Push — Auto confirmed. Receipt: {receipt}',
                )
                logger.info(f"Payment record created for invoice {tx.invoice.pk}")

                invoice_payments = getattr(tx.invoice, 'payments')
                total_paid = sum(p.amount for p in invoice_payments.all())
                tx.invoice.status = 'paid' if total_paid >= tx.invoice.total else 'partial'
                tx.invoice.save()
                logger.info(f"Invoice {tx.invoice.pk} status updated to {tx.invoice.status}")

            else:
                logger.warning(f"Payment failed: result_code={result_code}, result_desc={result_desc}")
                tx.status      = 'failed'
                tx.result_desc = result_desc
                tx.save()

        except Exception as e:
            logger.error(f"Callback error: {str(e)}", exc_info=True)

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})


@login_required
def mpesa_waiting(request, checkout_request_id):
    try:
        tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
    except MpesaTransaction.DoesNotExist:
        return redirect('billing_dashboard')
    return render(request, 'billing/mpesa_waiting.html', {
        'invoice':              tx.invoice,
        'phone':                tx.phone_number,
        'amount':               tx.amount,
        'checkout_request_id':  checkout_request_id,
    })


@login_required
def mpesa_payment_status(request, checkout_request_id):
    try:
        tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
        return JsonResponse({
            'status':  tx.status,
            'receipt': getattr(tx, 'mpesa_receipt', ''),
            'amount':  str(tx.amount),
        })
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'status': 'not_found'})