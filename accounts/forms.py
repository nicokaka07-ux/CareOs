import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from .models import StaffUser

# ── Allowed email providers ──────────────────────────────────────────────────
ALLOWED_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'yahoo.co.uk', 'yahoo.co.ke',
    'outlook.com', 'hotmail.com', 'hotmail.co.uk',
    'icloud.com', 'me.com', 'mac.com',
    'protonmail.com', 'proton.me',
    'live.com', 'msn.com',
    'aol.com',
    'zoho.com',
    'yandex.com', 'yandex.ru',
    'gmx.com', 'gmx.net',
}


def validate_common_email(value):
    """Reject obscure or disposable email domains."""
    if not value:
        return
    domain = value.split('@')[-1].lower()
    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            f'Please use a recognised email provider (e.g. Gmail, Yahoo, Outlook). '
            f'"{domain}" is not accepted.'
        )


def validate_strong_password(value):
    """Require uppercase, lowercase, digit, and special character."""
    errors = []
    if len(value) < 8:
        errors.append('at least 8 characters')
    if not re.search(r'[A-Z]', value):
        errors.append('at least one uppercase letter (A-Z)')
    if not re.search(r'[a-z]', value):
        errors.append('at least one lowercase letter (a-z)')
    if not re.search(r'\d', value):
        errors.append('at least one number (0-9)')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]', value):
        errors.append('at least one special character (!@#$%^&* etc.)')
    if errors:
        raise ValidationError(
            'Password must contain: ' + ', '.join(errors) + '.'
        )


class StaffCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        validators=[validate_common_email],
        help_text='Use a recognised provider: Gmail, Yahoo, Outlook, iCloud, etc.'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_password1'}),
        validators=[validate_strong_password],
        help_text=(
            'Must be at least 8 characters and include: '
            'uppercase letter, lowercase letter, number, and special character.'
        ),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter the same password again to confirm.',
    )

    class Meta:
        model  = StaffUser
        fields = [
            'first_name', 'last_name', 'username',
            'email', 'role', 'phone', 'department',
            'profile_photo', 'password1', 'password2',
        ]
        widgets = {
            'first_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'username':    forms.TextInput(attrs={'class': 'form-control'}),
            'role':        forms.Select(attrs={'class': 'form-select'}),
            'phone':       forms.TextInput(attrs={'class': 'form-control'}),
            'department':  forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if StaffUser.objects.filter(email__iexact=email).exists():
            raise ValidationError('A staff account with this email already exists.')
        return email


class StaffPasswordChangeForm(SetPasswordForm):
    """Used when admin resets a staff member's password."""
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_new_password1'}),
        validators=[validate_strong_password],
        help_text=(
            'Must be at least 8 characters and include: '
            'uppercase letter, lowercase letter, number, and special character.'
        ),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )