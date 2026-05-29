from django.urls import path
from . import views

urlpatterns = [
    path('',                         views.admin_dashboard,      name='admin_dashboard'),
    path('audit/',                   views.audit_log_list,       name='audit_log_list'),
    path('staff/',                   views.staff_list,           name='staff_list'),
    path('staff/create/',            views.create_staff,         name='create_staff'),        # ← new
    path('staff/<int:pk>/password/', views.reset_staff_password, name='reset_staff_password'), # ← 
    path('staff/<int:pk>/toggle/', views.toggle_staff_status, name='toggle_staff_status'),
]