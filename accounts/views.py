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
    if request.user.is_superuser and not request.user.role:
        return redirect('admin_dashboard')
    role_map = {
        'receptionist': 'opd_dashboard',
        'nurse':        'triage_list',
        'doctor':       'emr_dashboard',
        'pharmacist':   'pharmacy_queue',
        'cashier':      'billing_dashboard',
        'admin':        'admin_dashboard',
    }
    return redirect(role_map.get(request.user.role, 'admin_dashboard'))