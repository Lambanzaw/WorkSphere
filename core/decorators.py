"""
WorkSphere RBAC Decorators
Role-Based Access Control — enforces admin vs employee permissions.
Only active employees can access the system.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import AuditLog


def admin_required(view_func):
    """
    Decorator: Only admin/staff users can access this view.
    Redirects employees to their dashboard with an access denied message.
    """
    @wraps(view_func)
    @login_required(login_url='/login/')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            # Check if user has admin role via profile
            if hasattr(request.user, 'employee_profile'):
                messages.error(request, "Access denied. This area is for administrators only.")
                return redirect('employee_dashboard')
            messages.error(request, "Access denied.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    """
    Decorator: Only active employees can access this view.
    Also checks employee status — inactive employees are logged out.
    """
    @wraps(view_func)
    @login_required(login_url='/login/')
    def wrapper(request, *args, **kwargs):
        # Admins/staff can also access employee views for support
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check employee profile exists
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, "No employee profile found for your account.")
            return redirect('login')

        # HR Rule: Only active employees can log in
        employee = request.user.employee_profile
        if employee.status != 'active':
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, f"Your account is {employee.status}. Please contact HR.")
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


def log_admin_action(action, model_name, description_template=None):
    """
    Decorator factory: Automatically logs admin actions to AuditLog.
    HR Rule: All admin actions must be logged (audit trail).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            # Log successful POST actions
            if request.method == 'POST':
                obj_id = kwargs.get('pk') or kwargs.get('id')
                desc = description_template or f"Admin performed {action} on {model_name}"
                ip = get_client_ip(request)
                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    model_name=model_name,
                    object_id=obj_id,
                    description=desc,
                    ip_address=ip,
                )
            return response
        return wrapper
    return decorator


def get_client_ip(request):
    """Extract real client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
