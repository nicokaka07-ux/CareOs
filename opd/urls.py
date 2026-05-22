from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.opd_dashboard,             name='opd_dashboard'),
    path('patients/',                     views.patient_list,              name='patient_list'),
    path('patients/register/',            views.register_patient,          name='register_patient'),
    path('patients/<int:pk>/',            views.patient_detail,            name='patient_detail'),
    path('appointments/book/',            views.book_appointment,          name='book_appointment'),
    path('appointments/queue/',           views.queue_board,               name='queue_board'),
    path('appointments/<int:pk>/status/', views.update_appointment_status, name='update_appointment_status'),
    path('mortality/',                    views.mortality_list,            name='mortality_list'),
    path('mortality/record/',             views.record_mortality,          name='record_mortality'),
]