import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Invoice, Payment, MpesaTransaction
from .mpesa import stk_push
from opd.models import Patient, Appointment
from accounts.decorators import role_required

@login_required
@role_required('cashier','admin')
def billing_dashboard(request):
    today = timezone.now().date()
    return render(request, 'billing/dashboard.html', {
        'invoices':      Invoice.objects.filter(created_at__date=today).select_related('patient'),
        'total_revenue': Payment.objects.filter(paid_at__date=today).aggregate(t=Sum('amount'))['t'] or 0,
        'unpaid_count':  Invoice.objects.filter(status='unpaid').count(),
        'today':         today,
    })

@login_required
@role_required('cashier','admin')
def create_invoice(request):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient'))
        invoice = Invoice.objects.create(
            patient=patient,
            consultation_fee=request.POST.get('consultation_fee',0),
            lab_fee=request.POST.get('lab_fee',0),
            pharmacy_fee=request.POST.get('pharmacy_fee',0),
            other_fee=request.POST.get('other_fee',0),
            discount=request.POST.get('discount',0),
            notes=request.POST.get('notes',''),
            created_by=request.user,
        )
        messages.success(request, f'Invoice {invoice.invoice_number} created.')
        return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'billing/create_invoice.html',
                  {'patients': Patient.objects.filter(is_active=True)})

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'billing/invoice_detail.html',
                  {'invoice':invoice,'payments':invoice.payments.all()})

@login_required
@role_required('cashier','admin')
def record_payment(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        amount = float(request.POST.get('amount',0))
        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('invoice_detail', pk=invoice.pk)
        Payment.objects.create(
            invoice=invoice, method=request.POST.get('method'),
            amount=amount, reference=request.POST.get('reference',''),
            received_by=request.user, notes=request.POST.get('notes',''),
        )
        total_paid    = sum(p.amount for p in invoice.payments.all())
        invoice.status= 'paid' if total_paid >= invoice.total else 'partial'
        invoice.save()
        messages.success(request, f'Payment of KES {amount} recorded.')
        return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'billing/record_payment.html', {'invoice':invoice})

@login_required
@role_required('cashier','admin')
def mpesa_stk_push(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        phone  = request.POST.get('phone_number','').strip()
        amount = request.POST.get('amount', invoice.balance)
        
        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect('invoice_detail', pk=invoice.pk)
        
        # Attempt STK push
        result = stk_push(phone, float(amount), invoice.invoice_number)
        
        if result.get('ResponseCode') == '0':
            MpesaTransaction.objects.create(
                invoice=invoice, phone_number=phone, amount=amount,
                checkout_request_id=result.get('CheckoutRequestID',''),
                merchant_request_id=result.get('MerchantRequestID',''),
            )
            messages.success(request, f'M-Pesa prompt sent to {phone}. Patient will receive a pop-up on their phone.')
        else:
            error_msg = result.get('errorMessage', result.get('ResponseDescription', 'Unknown error'))
            messages.error(request, f"STK Push failed: {error_msg}")
        
        return redirect('invoice_detail', pk=invoice.pk)
    
    return render(request, 'billing/mpesa_push.html', {'invoice':invoice})

@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            callback    = data.get('Body',{}).get('stkCallback',{})
            checkout_id = callback.get('CheckoutRequestID')
            result_code = callback.get('ResultCode')
            try:
                tx = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
            except MpesaTransaction.DoesNotExist:
                return JsonResponse({'status':'not found'})
            if result_code == 0:
                items   = callback.get('CallbackMetadata',{}).get('Item',[])
                receipt = next((i.get('Value','') for i in items if i.get('Name')=='MpesaReceiptNumber'),'')
                tx.status        = 'success'
                tx.mpesa_receipt = receipt
                tx.completed_at  = timezone.now()
                tx.save()
                Payment.objects.create(
                    invoice=tx.invoice, method='mpesa',
                    amount=tx.amount, reference=receipt, notes='STK Push auto-confirmed')
                total_paid = sum(p.amount for p in tx.invoice.payments.all())
                tx.invoice.status = 'paid' if total_paid >= tx.invoice.total else 'partial'
                tx.invoice.save()
            else:
                tx.status = 'failed'
                tx.save()
        except Exception as e:
            return JsonResponse({'status': f'Error: {e}'})
    return JsonResponse({'status':'ok'})