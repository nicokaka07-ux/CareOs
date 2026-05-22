from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            return render(request, '403.html', status=403)
        return wrapper
    return decorator