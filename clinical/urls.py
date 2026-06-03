from django.urls import path
from . import views

urlpatterns = [
    path('triage/',                             views.triage_list,           name='triage_list'),
    path('triage/<int:appointment_pk>/',        views.record_triage,         name='record_triage'),
    path('emr/',                                views.emr_dashboard,         name='emr_dashboard'),
    path('emr/<int:appointment_pk>/',           views.patient_emr,           name='patient_emr'),
    path('emr/<int:appointment_pk>/save/',      views.save_consultation,     name='save_consultation'),
    path('emr/<int:appointment_pk>/lab/',       views.add_lab_order,         name='add_lab_order'),
    path('emr/<int:appointment_pk>/prescribe/', views.add_prescription,      name='add_prescription'),
    path('emr/<int:appointment_pk>/complete/',  views.complete_consultation, name='complete_consultation'),
path('lab-order/<int:pk>/delete/', views.delete_lab_order, name='delete_lab_order'),
path('prescription/<int:pk>/delete/', views.delete_prescription, name='delete_prescription'),
]