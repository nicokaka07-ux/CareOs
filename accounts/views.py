from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request,
            username=request.POST.get('username'),
            password=request.POST.get('password'))
        if user:
            login(request, user)
            messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_redirect(request):
    # All doctor specializations go to EMR
    doctor_roles = [
        'doctor','surgeon','physician','pediatrician','gynecologist',
        'cardiologist','neurologist','neurosurgeon','orthopedic',
        'dermatologist','psychiatrist','radiologist','anesthesiologist',
        'urologist','oncologist','ent','ophthalmologist','dentist',
        'physiotherapist',
    ]
    role = request.user.role
    if role in doctor_roles:
        return redirect('emr_dashboard')
    role_map = {
        'receptionist':   'opd_dashboard',
        'nurse':          'triage_list',
        'lab_technician': 'triage_list',
        'pharmacist':     'pharmacy_queue',
        'cashier':        'billing_dashboard',
        'admin':          'admin_dashboard',
        'nutritionist':   'opd_dashboard',
    }
    return redirect(role_map.get(role, 'opd_dashboard'))