from django.urls import path
from . import views

urlpatterns = [
    path('',       views.admin_dashboard, name='admin_dashboard'),
    path('audit/', views.audit_log_list,  name='audit_log_list'),
    path('staff/', views.staff_list,      name='staff_list'),
]