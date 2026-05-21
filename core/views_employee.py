"""
WorkSphere Employee Management Views
Admin: Full CRUD on employees
Employee: View own profile only
HR Rules: Unique ID/email, active status validation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Employee, Department, LeaveBalance, LeaveType, AuditLog
from .forms import EmployeeCreateForm, EmployeeEditForm, DepartmentForm
from .decorators import admin_required, employee_required, get_client_ip


# ─── ADMIN DASHBOARD ───────────────────────────────────────────────────────────
@admin_required
def admin_dashboard(request):
    """Admin dashboard with HR summary statistics."""
    today = timezone.now().date()

    total_employees = Employee.objects.filter(status='active').count()
    attendance_today = __import__('core.models', fromlist=['Attendance']).Attendance.objects.filter(date=today).count()

    from .models import LeaveRequest, Payroll
    pending_leaves = LeaveRequest.objects.filter(status='pending').count()

    # Payroll summary for current month
    current_month = today.month
    current_year = today.year
    payroll_count = Payroll.objects.filter(month=current_month, year=current_year).count()

    # Recent activity
    recent_leaves = LeaveRequest.objects.select_related('employee').order_by('-filed_on')[:5]
    recent_audit = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]

    # Department breakdown
    departments = Department.objects.all()
    dept_data = []
    for dept in departments:
        count = Employee.objects.filter(department=dept, status='active').count()
        if count > 0:
            dept_data.append({'name': dept.name, 'count': count})

    context = {
        'total_employees': total_employees,
        'attendance_today': attendance_today,
        'pending_leaves': pending_leaves,
        'payroll_count': payroll_count,
        'recent_leaves': recent_leaves,
        'recent_audit': recent_audit,
        'dept_data': dept_data,
        'today': today,
    }
    return render(request, 'admin_dashboard.html', context)


# ─── EMPLOYEE DASHBOARD ────────────────────────────────────────────────────────
@employee_required
def employee_dashboard(request):
    """Employee's personal dashboard."""
    from .models import Attendance, LeaveRequest, Payroll

    employee = request.user.employee_profile
    today = timezone.now().date()

    # Today's attendance
    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()

    # Recent attendance (last 7 days)
    recent_attendance = Attendance.objects.filter(
        employee=employee
    ).order_by('-date')[:7]

    # Leave requests
    recent_leaves = LeaveRequest.objects.filter(employee=employee).order_by('-filed_on')[:5]
    pending_leaves = LeaveRequest.objects.filter(employee=employee, status='pending').count()

    # Latest payslip
    latest_payroll = Payroll.objects.filter(employee=employee).first()

    context = {
        'employee': employee,
        'today': today,
        'today_attendance': today_attendance,
        'recent_attendance': recent_attendance,
        'recent_leaves': recent_leaves,
        'pending_leaves': pending_leaves,
        'latest_payroll': latest_payroll,
    }
    return render(request, 'employee_dashboard.html', context)


# ─── EMPLOYEE LIST ─────────────────────────────────────────────────────────────
@admin_required
def employee_list(request):
    """Admin view of all employees with search/filter."""
    employees = Employee.objects.select_related('department', 'user').all()

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        employees = employees.filter(
            first_name__icontains=search
        ) | employees.filter(
            last_name__icontains=search
        ) | employees.filter(
            employee_id__icontains=search
        ) | employees.filter(
            email__icontains=search
        )

    # Filter by department
    dept_filter = request.GET.get('department', '')
    if dept_filter:
        employees = employees.filter(department_id=dept_filter)

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        employees = employees.filter(status=status_filter)

    departments = Department.objects.all()
    context = {
        'employees': employees,
        'departments': departments,
        'search': search,
        'dept_filter': dept_filter,
        'status_filter': status_filter,
    }
    return render(request, 'employees/list.html', context)


# ─── EMPLOYEE CREATE ───────────────────────────────────────────────────────────
@admin_required
def employee_create(request):
    """Create new employee with linked User account."""
    if request.method == 'POST':
        form = EmployeeCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the User account
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'],
                        email=form.cleaned_data['email'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                    )

                    # Create Employee profile
                    employee = form.save(commit=False)
                    employee.user = user
                    employee.save()

                    # Auto-allocate leave balances for current year
                    current_year = timezone.now().year
                    for leave_type in LeaveType.objects.all():
                        LeaveBalance.objects.create(
                            employee=employee,
                            leave_type=leave_type,
                            year=current_year,
                            allocated_days=leave_type.max_days,
                        )

                    # Audit log
                    AuditLog.objects.create(
                        user=request.user,
                        action='create',
                        model_name='Employee',
                        object_id=employee.id,
                        description=f"Created employee: {employee.get_full_name()} ({employee.employee_id})",
                        ip_address=get_client_ip(request),
                    )

                    messages.success(request, f"Employee {employee.get_full_name()} created successfully!")
                    return redirect('employee_list')

            except Exception as e:
                messages.error(request, f"Error creating employee: {str(e)}")
    else:
        form = EmployeeCreateForm()

    return render(request, 'employees/create.html', {'form': form})


# ─── EMPLOYEE DETAIL ───────────────────────────────────────────────────────────
@admin_required
def employee_detail(request, pk):
    """View full employee profile (admin)."""
    from .models import Attendance, LeaveRequest

    employee = get_object_or_404(Employee, pk=pk)
    recent_attendance = Attendance.objects.filter(employee=employee).order_by('-date')[:10]
    leave_history = LeaveRequest.objects.filter(employee=employee).order_by('-filed_on')[:10]
    leave_balances = LeaveBalance.objects.filter(
        employee=employee,
        year=timezone.now().year
    ).select_related('leave_type')

    context = {
        'employee': employee,
        'recent_attendance': recent_attendance,
        'leave_history': leave_history,
        'leave_balances': leave_balances,
    }
    return render(request, 'employees/detail.html', context)


# ─── EMPLOYEE EDIT ─────────────────────────────────────────────────────────────
@admin_required
def employee_edit(request, pk):
    """Edit employee details."""
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == 'POST':
        form = EmployeeEditForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            employee = form.save()

            # Sync user email
            employee.user.email = employee.email
            employee.user.first_name = employee.first_name
            employee.user.last_name = employee.last_name
            # HR Rule: Inactive employee cannot log in
            employee.user.is_active = (employee.status == 'active')
            employee.user.save()

            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='Employee',
                object_id=employee.id,
                description=f"Updated employee: {employee.get_full_name()} ({employee.employee_id})",
                ip_address=get_client_ip(request),
            )

            messages.success(request, f"Employee {employee.get_full_name()} updated successfully!")
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeEditForm(instance=employee)

    return render(request, 'employees/edit.html', {'form': form, 'employee': employee})


# ─── OWN PROFILE (EMPLOYEE) ────────────────────────────────────────────────────
@employee_required
def my_profile(request):
    """Employee views their own profile."""
    employee = request.user.employee_profile
    leave_balances = LeaveBalance.objects.filter(
        employee=employee,
        year=timezone.now().year
    ).select_related('leave_type')

    return render(request, 'employees/my_profile.html', {
        'employee': employee,
        'leave_balances': leave_balances,
    })
