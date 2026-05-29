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
@role_required('cashier', 'admin')
def billing_dashboard(request):
    today = timezone.now().date()
    return render(request, 'billing/dashboard.html', {
        'invoices':        Invoice.objects.filter(created_at__date=today).select_related('patient'),
        'all_invoices':    Invoice.objects.select_related('patient').order_by('-created_at'),
        'unpaid_invoices': Invoice.objects.filter(status='unpaid').select_related('patient').order_by('-created_at'),
        'total_revenue':   Payment.objects.filter(paid_at__date=today).aggregate(t=Sum('amount'))['t'] or 0,
        'unpaid_count':    Invoice.objects.filter(status='unpaid').count(),
        'today':           today,
    })


@login_required
@role_required('cashier', 'admin')
def create_invoice(request):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient'))
        invoice = Invoice.objects.create(
            patient=patient,
            consultation_fee=request.POST.get('consultation_fee', 0),
            lab_fee=request.POST.get('lab_fee', 0),
            pharmacy_fee=request.POST.get('pharmacy_fee', 0),
            other_fee=request.POST.get('other_fee', 0),
            discount=request.POST.get('discount', 0),
            notes=request.POST.get('notes', ''),
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
                  {'invoice': invoice, 'payments': invoice.payments.all()})


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
            invoice=invoice, method=request.POST.get('method'),
            amount=amount, reference=request.POST.get('reference', ''),
            received_by=request.user, notes=request.POST.get('notes', ''),
        )
        total_paid = sum(p.amount for p in invoice.payments.all())
        invoice.status = 'paid' if total_paid >= invoice.total else 'partial'
        invoice.save()
        messages.success(request, f'Payment of KES {amount} recorded.')
        return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'billing/record_payment.html', {'invoice': invoice})


@login_required
@role_required('cashier', 'admin')
def mpesa_stk_push(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        phone = request.POST.get('phone_number', '').strip()
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
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            print(f"MPESA CALLBACK RECEIVED: {data}")
            callback    = data.get('Body', {}).get('stkCallback', {})
            checkout_id = callback.get('CheckoutRequestID')
            result_code = callback.get('ResultCode')
            result_desc = callback.get('ResultDesc', '')

            try:
                tx = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
            except MpesaTransaction.DoesNotExist:
                print(f"Transaction not found: {checkout_id}")
                return JsonResponse({'status': 'not found'})

            if result_code == 0:
                items = callback.get('CallbackMetadata', {}).get('Item', [])
                receipt = ''
                amount  = 0
                phone   = ''

                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        receipt = item.get('Value', '')
                    elif item.get('Name') == 'Amount':
                        amount = item.get('Value', 0)
                    elif item.get('Name') == 'PhoneNumber':
                        phone = item.get('Value', '')

                print(f"Payment successful: {receipt} — KES {amount}")

                tx.status        = 'success'
                tx.mpesa_receipt = receipt
                tx.result_desc   = result_desc
                tx.completed_at  = timezone.now()
                tx.save()

                Payment.objects.create(
                    invoice=tx.invoice,
                    method='mpesa',
                    amount=tx.amount,
                    reference=receipt,
                    received_by=None,
                    notes=f'M-Pesa STK Push — Auto confirmed. Receipt: {receipt}',
                )

                total_paid = sum(p.amount for p in tx.invoice.payments.all())
                if total_paid >= tx.invoice.total:
                    tx.invoice.status = 'paid'
                elif total_paid > 0:
                    tx.invoice.status = 'partial'
                tx.invoice.save()

                print(f"Invoice {tx.invoice.invoice_number} updated to: {tx.invoice.status}")

            else:
                tx.status      = 'failed'
                tx.result_desc = result_desc
                tx.save()
                print(f"Payment failed: {result_desc}")

        except Exception as e:
            print(f"Callback error: {e}")

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})


@login_required
def mpesa_waiting(request, checkout_request_id):
    try:
        tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
    except MpesaTransaction.DoesNotExist:
        return redirect('billing_dashboard')
    return render(request, 'billing/mpesa_waiting.html', {
        'invoice': tx.invoice,
        'phone': tx.phone_number,
        'amount': tx.amount,
        'checkout_request_id': checkout_request_id,
    })


@login_required
def mpesa_payment_status(request, checkout_request_id):
    try:
        tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
        return JsonResponse({
            'status': tx.status,
            'receipt': getattr(tx, 'mpesa_receipt', ''),
            'amount': str(tx.amount),
        })
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'status': 'not_found'})