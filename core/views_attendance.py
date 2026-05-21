from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import datetime
import pytz

from .models import Attendance, Employee, SpecialWorkingDay, AuditLog
from .forms import AttendanceClockInForm, AttendanceClockOutForm, AttendanceAdminForm
from .decorators import admin_required, employee_required, get_client_ip

PH_TZ = pytz.timezone('Asia/Manila')


def get_ph_now():
    return timezone.now().astimezone(PH_TZ)


@employee_required
def clock_in(request):
    employee = request.user.employee_profile
    now_ph   = get_ph_now()
    today    = now_ph.date()
    now_time = now_ph.time()

    existing = Attendance.objects.filter(employee=employee, date=today).first()
    if existing:
        messages.warning(request, "You have already clocked in today.")
        return redirect('my_attendance')

    if request.method == 'POST':
        form = AttendanceClockInForm(request.POST, employee=employee)
        if form.is_valid():
            with transaction.atomic():
                standard_start = datetime.time(8, 0, 0)
                is_late = now_time > standard_start
                status  = 'late' if is_late else 'present'

                attendance = Attendance.objects.create(
                    employee = employee,
                    date     = today,
                    time_in  = now_time,
                    status   = status,
                )

                messages.success(
                    request,
                    f"Clocked in at {now_time.strftime('%I:%M %p')}. "
                    + ("You are late today." if is_late else "Have a productive day!")
                )
                return redirect('my_attendance')
    else:
        form = AttendanceClockInForm(employee=employee)

    is_weekend = today.weekday() >= 5
    is_special = SpecialWorkingDay.objects.filter(date=today).exists()

    return render(request, 'attendance/clock_in.html', {
        'form':       form,
        'today':      today,
        'now_time':   now_time,
        'is_weekend': is_weekend,
        'is_special': is_special,
        'existing':   existing,
    })


@employee_required
def clock_out(request):
    employee = request.user.employee_profile
    now_ph   = get_ph_now()
    today    = now_ph.date()
    now_time = now_ph.time()

    attendance = Attendance.objects.filter(employee=employee, date=today).first()

    if not attendance:
        messages.error(request, "You haven't clocked in today yet.")
        return redirect('my_attendance')

    if attendance.time_out:
        messages.warning(request, "You have already clocked out today.")
        return redirect('my_attendance')

    if request.method == 'POST':
        form = AttendanceClockOutForm(request.POST, attendance=attendance)
        if form.is_valid():
            with transaction.atomic():
                attendance.time_out = now_time

                standard_end = datetime.time(17, 0, 0)
                if now_time > standard_end:
                    time_out_dt  = datetime.datetime.combine(today, now_time)
                    std_end_dt   = datetime.datetime.combine(today, standard_end)
                    overtime_delta = time_out_dt - std_end_dt
                    attendance.overtime_hours = round(overtime_delta.total_seconds() / 3600, 2)

                attendance.save()

                hours_worked = attendance.get_hours_worked()
                messages.success(
                    request,
                    f"Clocked out at {now_time.strftime('%I:%M %p')}. "
                    f"Total hours worked: {hours_worked:.1f}h."
                )
                return redirect('my_attendance')
    else:
        form = AttendanceClockOutForm(attendance=attendance)

    return render(request, 'attendance/clock_out.html', {
        'form':       form,
        'attendance': attendance,
        'today':      today,
        'now_time':   now_time,
    })


@employee_required
def my_attendance(request):
    employee = request.user.employee_profile
    today    = get_ph_now().date()

    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year',  today.year))

    attendance_records = Attendance.objects.filter(
        employee   = employee,
        date__month = month,
        date__year  = year,
    ).order_by('-date')

    total_present = attendance_records.filter(status__in=['present', 'late', 'overtime']).count()
    total_late    = attendance_records.filter(status='late').count()
    total_absent  = attendance_records.filter(status='absent').count()

    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()

    context = {
        'attendance_records': attendance_records,
        'today':              today,
        'today_attendance':   today_attendance,
        'month':              month,
        'year':               year,
        'total_present':      total_present,
        'total_late':         total_late,
        'total_absent':       total_absent,
        'months':             [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        'years':              range(today.year - 2, today.year + 1),
    }
    return render(request, 'attendance/my_attendance.html', context)


@admin_required
def admin_attendance_list(request):
    today = get_ph_now().date()

    date_filter = request.GET.get('date', str(today))
    emp_filter  = request.GET.get('employee', '')

    records = Attendance.objects.select_related('employee', 'employee__department').order_by('-date', 'employee')

    if date_filter:
        records = records.filter(date=date_filter)
    if emp_filter:
        records = records.filter(employee_id=emp_filter)

    employees = Employee.objects.filter(status='active').order_by('last_name')

    context = {
        'records':     records,
        'today':       today,
        'date_filter': date_filter,
        'emp_filter':  emp_filter,
        'employees':   employees,
    }
    return render(request, 'attendance/admin_list.html', context)


@admin_required
def admin_attendance_override(request, pk=None):
    attendance = get_object_or_404(Attendance, pk=pk) if pk else None

    if request.method == 'POST':
        form = AttendanceAdminForm(request.POST, instance=attendance)
        if form.is_valid():
            with transaction.atomic():
                att = form.save(commit=False)
                att.admin_override = True
                att.save()

                AuditLog.objects.create(
                    user        = request.user,
                    action      = 'override',
                    model_name  = 'Attendance',
                    object_id   = att.id,
                    description = f"Admin overrode attendance for {att.employee.get_full_name()} on {att.date}. Reason: {att.override_reason}",
                    ip_address  = get_client_ip(request),
                )

                messages.success(request, f"Attendance record updated for {att.employee.get_full_name()}.")
                return redirect('admin_attendance_list')
    else:
        form = AttendanceAdminForm(instance=attendance)

    return render(request, 'attendance/override.html', {
        'form':       form,
        'attendance': attendance,
    })