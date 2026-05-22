from django.urls import path
from . import views

urlpatterns = [
    path('',                                  views.billing_dashboard, name='billing_dashboard'),
    path('invoice/create/',                   views.create_invoice,    name='create_invoice'),
    path('invoice/<int:pk>/',                 views.invoice_detail,    name='invoice_detail'),
    path('invoice/<int:invoice_pk>/pay/',     views.record_payment,    name='record_payment'),
    path('invoice/<int:invoice_pk>/mpesa/',   views.mpesa_stk_push,    name='mpesa_stk_push'),
    path('mpesa/callback/',                   views.mpesa_callback,    name='mpesa_callback'),
]