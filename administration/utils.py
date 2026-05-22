from .models import AuditLog

def log_action(request, action, model_name, description, object_id=''):
    ip = request.META.get('HTTP_X_FORWARDED_FOR','').split(',')[0].strip() \
         or request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action, model_name=model_name,
        object_id=str(object_id), description=description,
        ip_address=ip or None,
    )