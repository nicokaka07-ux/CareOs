from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from .models import StaffUser, OTPCode

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


def verify_otp_view(request):
    """Verify OTP and log user in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Check if user has gone through login
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Please log in first.')
        return redirect('login')
    
    try:
        user = StaffUser.objects.get(id=user_id)
    except StaffUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp')
        
        try:
            otp = OTPCode.objects.get(user=user)
            
            # Check if OTP is expired
            if otp.is_expired():
                otp.delete()
                messages.error(request, 'OTP has expired. Please log in again.')
                del request.session['otp_user_id']
                del request.session['otp_username']
                return redirect('login')
            
            # Check if max attempts exceeded
            if otp.attempts >= otp.max_attempts:
                otp.delete()
                messages.error(request, 'Too many failed attempts. Please log in again.')
                del request.session['otp_user_id']
                del request.session['otp_username']
                return redirect('login')
            
            # Verify OTP code
            if otp.code == otp_code:
                # OTP is valid, log user in
                login(request, user)
                otp.delete()
                # Clear session
                del request.session['otp_user_id']
                del request.session['otp_username']
                messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                # Increment attempts
                otp.increment_attempts()
                remaining = otp.max_attempts - otp.attempts
                messages.error(request, f'Invalid OTP. {remaining} attempts remaining.')
        
        except OTPCode.DoesNotExist:
            messages.error(request, 'OTP not found. Please log in again.')
            return redirect('login')
    
    return render(request, 'accounts/verify_otp.html', {
        'username': request.session.get('otp_username'),
        'email': user.email or settings.OTP_FALLBACK_EMAIL,
    })

def resend_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    try:
        user = StaffUser.objects.get(id=user_id)
    except StaffUser.DoesNotExist:
        messages.error(request, 'User not found. Please log in again.')
        return redirect('login')

    OTPCode.generate_otp(user)
    email_address = user.email or settings.OTP_FALLBACK_EMAIL
    messages.success(request, f'A new OTP has been sent to {email_address}.')
    return redirect('verify_otp')


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