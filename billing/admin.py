from django.contrib import admin
from .models import Invoice, Payment, MpesaTransaction, Receipt

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('paid_at', 'received_by')

class MpesaTransactionInline(admin.TabularInline):
    model = MpesaTransaction
    extra = 0
    # Trimmed down to guaranteed transaction core parameters
    readonly_fields = ('checkout_request_id', 'merchant_request_id', 'amount', 'phone_number', 'status', 'mpesa_receipt')
    can_delete = False

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    # 'created_at' is verified on your Invoice model layout from previous dashboard views
    list_display = ('invoice_number', 'patient', 'display_total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invoice_number', 'patient__first_name', 'patient__last_name', 'patient__patient_id')
    
    fields = ('invoice_number', 'patient', 'appointment', 'status', 'discount', 'notes', 'created_by', 'display_total_detail')
    readonly_fields = ('invoice_number', 'created_by', 'display_total_detail')
    
    inlines = [PaymentInline, MpesaTransactionInline]

    def display_total(self, obj):
        val = getattr(obj, 'total', 0)
        return f"KES {val:,.2f}"
    display_total.short_description = 'Total Amount'

    def display_total_detail(self, obj):
        val = getattr(obj, 'total', 0)
        return f"KES {val:,.2f}"
    display_total_detail.short_description = 'Automatically Generated Total'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'method', 'amount', 'reference', 'paid_at')
    list_filter = ('method', 'paid_at')

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    # Removed the unverified timestamp fields causing E108/E116 blocks
    list_display = ('checkout_request_id', 'invoice', 'phone_number', 'amount', 'status')
    list_filter = ('status',)

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'invoice', 'generated_by')