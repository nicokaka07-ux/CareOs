from django.urls import path
from . import views

urlpatterns = [
    path('',                                views.pharmacy_queue, name='pharmacy_queue'),
    path('dispense/<int:prescription_pk>/', views.dispense,       name='dispense'),
    path('inventory/',                      views.drug_inventory, name='drug_inventory'),
    path('inventory/add/',                  views.add_drug,       name='add_drug'),
    path('inventory/restock/<int:drug_pk>/',views.restock_drug,   name='restock_drug'),
]