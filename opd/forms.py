from django import forms
from .models import Patient, Appointment, Department
from accounts.models import StaffUser

class PatientRegistrationForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    class Meta:
        model  = Patient
        fields = ['first_name','last_name','date_of_birth','gender','blood_group',
                  'national_id','photo','phone','email','address','county',
                  'emergency_name','emergency_relationship','emergency_phone',
                  'known_allergies','chronic_conditions','current_medications']
        widgets = {
            'first_name':              forms.TextInput(attrs={'class':'form-control'}),
            'last_name':               forms.TextInput(attrs={'class':'form-control'}),
            'gender':                  forms.Select(attrs={'class':'form-select'}),
            'blood_group':             forms.Select(attrs={'class':'form-select'}),
            'national_id':             forms.TextInput(attrs={'class':'form-control'}),
            'phone':                   forms.TextInput(attrs={'class':'form-control'}),
            'email':                   forms.EmailInput(attrs={'class':'form-control'}),
            'address':                 forms.Textarea(attrs={'class':'form-control','rows':2}),
            'county':                  forms.TextInput(attrs={'class':'form-control'}),
            'emergency_name':          forms.TextInput(attrs={'class':'form-control'}),
            'emergency_relationship':  forms.TextInput(attrs={'class':'form-control'}),
            'emergency_phone':         forms.TextInput(attrs={'class':'form-control'}),
            'known_allergies':         forms.Textarea(attrs={'class':'form-control','rows':2}),
            'chronic_conditions':      forms.Textarea(attrs={'class':'form-control','rows':2}),
            'current_medications':     forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

class AppointmentForm(forms.ModelForm):
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    scheduled_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type':'time','class':'form-control'}))
    class Meta:
        model  = Appointment
        fields = ['patient','doctor','department','scheduled_date',
                  'scheduled_time','priority','reason']
        widgets = {
            'patient':    forms.Select(attrs={'class':'form-select'}),
            'doctor':     forms.Select(attrs={'class':'form-select'}),
            'department': forms.Select(attrs={'class':'form-select'}),
            'priority':   forms.Select(attrs={'class':'form-select'}),
            'reason':     forms.Textarea(attrs={'class':'form-control','rows':3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = StaffUser.objects.filter(role='doctor', is_active=True)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)