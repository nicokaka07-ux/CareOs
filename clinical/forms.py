from django import forms
from .models import TriageRecord, Consultation, LabOrder, Prescription

class TriageForm(forms.ModelForm):
    class Meta:
        model  = TriageRecord
        fields = ['blood_pressure_systolic','blood_pressure_diastolic','temperature',
                  'heart_rate','respiratory_rate','oxygen_saturation','weight','height',
                  'pain_scale','chief_complaint','nurse_notes']
        widgets = {
            'blood_pressure_systolic':  forms.NumberInput(attrs={'class':'form-control'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class':'form-control'}),
            'temperature':              forms.NumberInput(attrs={'class':'form-control','step':'0.1'}),
            'heart_rate':               forms.NumberInput(attrs={'class':'form-control'}),
            'respiratory_rate':         forms.NumberInput(attrs={'class':'form-control'}),
            'oxygen_saturation':        forms.NumberInput(attrs={'class':'form-control'}),
            'weight':                   forms.NumberInput(attrs={'class':'form-control','step':'0.1'}),
            'height':                   forms.NumberInput(attrs={'class':'form-control','step':'0.1'}),
            'pain_scale':               forms.NumberInput(attrs={'class':'form-control','min':0,'max':10}),
            'chief_complaint':          forms.Textarea(attrs={'class':'form-control','rows':3}),
            'nurse_notes':              forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class ConsultationForm(forms.ModelForm):
    follow_up_date = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    class Meta:
        model  = Consultation
        fields = ['presenting_complaint','history_of_illness','examination_findings',
                  'diagnosis','treatment_plan','doctor_notes','follow_up_date']
        widgets = {
            'presenting_complaint': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'history_of_illness':   forms.Textarea(attrs={'class':'form-control','rows':3}),
            'examination_findings': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'diagnosis':            forms.Textarea(attrs={'class':'form-control','rows':3}),
            'treatment_plan':       forms.Textarea(attrs={'class':'form-control','rows':3}),
            'doctor_notes':         forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

class LabOrderForm(forms.ModelForm):
    class Meta:
        model   = LabOrder
        fields  = ['test_name','instructions']
        widgets = {
            'test_name':    forms.TextInput(attrs={'class':'form-control','placeholder':'e.g. Full Blood Count'}),
            'instructions': forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model   = Prescription
        fields  = ['medication_name','dosage','frequency','duration','instructions','quantity']
        widgets = {
            'medication_name': forms.TextInput(attrs={'class':'form-control'}),
            'dosage':          forms.TextInput(attrs={'class':'form-control'}),
            'frequency':       forms.TextInput(attrs={'class':'form-control'}),
            'duration':        forms.TextInput(attrs={'class':'form-control'}),
            'instructions':    forms.Textarea(attrs={'class':'form-control','rows':2}),
            'quantity':        forms.NumberInput(attrs={'class':'form-control'}),
        }