from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .forms import AttendanceAdminForm

import datetime

from .models import Employee, Department, Attendance, CompanySettings


# ── Auth ─────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ── Dashboard ─────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.now().date()
    total_employees = Employee.objects.filter(status='active').count()
    present_today   = Attendance.objects.filter(date=today, status__in=['present', 'late']).count()

    recent_attendance = Attendance.objects.filter(date=today).select_related('employee')[:10]

    context = {
        'total_employees': total_employees,
        'present_today':   present_today,
        'today':           today,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'core/dashboard.html', context)


# ── Employees ─────────────────────────────────────────────

@login_required
def employee_list(request):
    q      = request.GET.get('q', '')
    dept   = request.GET.get('dept', '')
    status = request.GET.get('status', '')

    employees = Employee.objects.select_related('department').all()

    if q:
        employees = employees.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(employee_id__icontains=q)
        )
    if dept:
        employees = employees.filter(department_id=dept)
    if status:
        employees = employees.filter(status=status)

    departments = Department.objects.all()
    context = {
        'employees':   employees,
        'departments': departments,
        'q':           q,
        'dept':        dept,
        'status':      status,
    }
    return render(request, 'core/employees.html', context)


@login_required
def employee_add(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        try:
            emp = Employee(
                employee_id  = request.POST.get('employee_id'),
                first_name   = request.POST.get('first_name'),
                last_name    = request.POST.get('last_name'),
                email        = request.POST.get('email'),
                phone        = request.POST.get('phone', ''),
                address      = request.POST.get('address', ''),
                position     = request.POST.get('position'),
                date_hired   = request.POST.get('date_hired'),
                basic_salary = request.POST.get('basic_salary') or 0,
                status       = request.POST.get('status', 'active'),
            )
            dept_id = request.POST.get('department')
            if dept_id:
                emp.department = Department.objects.get(pk=dept_id)
            emp.save()
            messages.success(request, f'Employee {emp.get_full_name()} added successfully.')
            return redirect('employee_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {'departments': departments}
    return render(request, 'core/employee_add.html', context)


@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    recent_attendance = Attendance.objects.filter(employee=employee).order_by('-date')[:10]
    context = {
        'employee': employee,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'core/employee_detail.html', context)


@login_required
def employee_edit(request, pk):
    employee    = get_object_or_404(Employee, pk=pk)
    departments = Department.objects.all()

    if request.method == 'POST':
        try:
            employee.first_name   = request.POST.get('first_name')
            employee.last_name    = request.POST.get('last_name')
            employee.email        = request.POST.get('email')
            employee.phone        = request.POST.get('phone', '')
            employee.address      = request.POST.get('address', '')
            employee.position     = request.POST.get('position')
            employee.date_hired   = request.POST.get('date_hired')
            employee.basic_salary = request.POST.get('basic_salary') or 0
            employee.status       = request.POST.get('status', 'active')
            dept_id = request.POST.get('department')
            if dept_id:
                employee.department = Department.objects.get(pk=dept_id)
            employee.save()
            messages.success(request, 'Employee updated successfully.')
            return redirect('employee_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {'employee': employee, 'departments': departments}
    return render(request, 'core/employee_edit.html', context)


@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        name = employee.get_full_name()
        employee.delete()
        messages.success(request, f'{name} has been deleted.')
        return redirect('employee_list')
    return render(request, 'core/employee_delete.html', {'employee': employee})


# ── Attendance ────────────────────────────────────────────

@login_required
def attendance_list(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            selected_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    records = Attendance.objects.filter(date=selected_date).select_related('employee', 'employee__department')
    employees = Employee.objects.filter(status='active').select_related('department')

    context = {
        'records':       records,
        'employees':     employees,
        'selected_date': selected_date,
    }
    return render(request, 'core/attendance.html', context)


@login_required
def clock_in(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        today  = timezone.now().date()
        now    = timezone.now().time()

        try:
            employee = Employee.objects.get(pk=emp_id)
            settings_obj = CompanySettings.objects.first()
            work_start = settings_obj.work_start if settings_obj else datetime.time(8, 0)

            # Check if already clocked in
            existing = Attendance.objects.filter(employee=employee, date=today).first()
            if existing and existing.time_in:
                messages.warning(request, f'{employee.get_full_name()} already clocked in today.')
                return redirect('attendance')

            # Calculate late minutes
            now_dt    = datetime.datetime.combine(today, now)
            start_dt  = datetime.datetime.combine(today, work_start)
            late_mins = max(0, int((now_dt - start_dt).total_seconds() / 60)) if now_dt > start_dt else 0
            status    = 'late' if late_mins > 0 else 'present'

            if existing:
                existing.time_in     = now
                existing.late_minutes = late_mins
                existing.status      = status
                existing.save()
            else:
                Attendance.objects.create(
                    employee     = employee,
                    date         = today,
                    time_in      = now,
                    late_minutes = late_mins,
                    status       = status,
                )

            messages.success(request, f'{employee.get_full_name()} clocked in at {now.strftime("%I:%M %p")}.')
        except Employee.DoesNotExist:
            messages.error(request, 'Employee not found.')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return redirect('attendance')


@login_required
def clock_out(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        today  = timezone.now().date()
        now    = timezone.now().time()

        try:
            employee = Employee.objects.get(pk=emp_id)
            record   = Attendance.objects.filter(employee=employee, date=today).first()

            if not record or not record.time_in:
                messages.warning(request, f'{employee.get_full_name()} has not clocked in yet.')
            elif record.time_out:
                messages.warning(request, f'{employee.get_full_name()} already clocked out today.')
            else:
                record.time_out = now
                record.save()
                messages.success(request, f'{employee.get_full_name()} clocked out at {now.strftime("%I:%M %p")}.')
        except Employee.DoesNotExist:
            messages.error(request, 'Employee not found.')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return redirect('attendance')


# ── Settings ──────────────────────────────────────────────

@login_required
def settings_view(request):
    obj, _ = CompanySettings.objects.get_or_create(pk=1)
    departments = Department.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_company':
            obj.company_name = request.POST.get('company_name', '')
            obj.address      = request.POST.get('address', '')
            obj.phone        = request.POST.get('phone', '')
            obj.email        = request.POST.get('email', '')
            obj.work_start   = request.POST.get('work_start') or '08:00'
            obj.work_end     = request.POST.get('work_end') or '17:00'
            obj.save()
            messages.success(request, 'Settings saved.')

        elif action == 'add_dept':
            name = request.POST.get('dept_name', '').strip()
            if name:
                Department.objects.get_or_create(name=name)
                messages.success(request, f'Department "{name}" added.')
            else:
                messages.error(request, 'Department name cannot be empty.')

        elif action == 'delete_dept':
            dept_id = request.POST.get('dept_id')
            try:
                dept = Department.objects.get(pk=dept_id)
                dept.delete()
                messages.success(request, 'Department deleted.')
            except Department.DoesNotExist:
                messages.error(request, 'Department not found.')

        return redirect('settings')

    context = {'settings': obj, 'departments': departments}
    return render(request, 'core/settings.html', context)

@login_required
def attendance_override(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        form = AttendanceAdminForm(request.POST, instance=attendance)
        if form.is_valid():
            record = form.save(commit=False)
            record.admin_override = True
            record.save()
            messages.success(request, 'Attendance record updated successfully.')
            return redirect('admin_attendance_list')
    else:
        form = AttendanceAdminForm(instance=attendance)
    
    return render(request, 'core/attendance_override.html', {
        'attendance': attendance,
        'form': form,
    })