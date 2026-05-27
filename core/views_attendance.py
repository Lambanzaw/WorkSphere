from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import datetime
import calendar
import pytz

from .models import Attendance, Employee, SpecialWorkingDay, AuditLog, LeaveRequest
from .forms import AttendanceClockInForm, AttendanceClockOutForm, AttendanceAdminForm
from .decorators import admin_required, employee_required, get_client_ip

PH_TZ = pytz.timezone('Asia/Manila')


def get_ph_now():
    return timezone.now().astimezone(PH_TZ)


def auto_mark_absent_for_date(target_date):
    if target_date.weekday() >= 5:
        return 0

    active_employees = Employee.objects.filter(status='active')
    marked = 0

    for emp in active_employees:
        # Skip if employee was not yet hired on this date
        if emp.date_hired > target_date:
            continue

        exists = Attendance.objects.filter(
            employee=emp,
            date=target_date
        ).exists()

        if not exists:
            Attendance.objects.create(
                employee=emp,
                date=target_date,
                status='absent',
                time_in=None,
                time_out=None,
                admin_override=True,
                notes='Auto-marked absent — no clock-in recorded.',
            )
            marked += 1

    return marked

def auto_mark_absent_past_days(days_back=30):
    today = get_ph_now().date()
    total = 0
    for i in range(1, days_back + 1):
        target = today - datetime.timedelta(days=i)
        if target.weekday() >= 5:
            continue
        count = auto_mark_absent_for_date(target)
        total += count
    return total


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

    # Block clock-in outside allowed hours (6:00 AM to 5:00 PM only)
    allowed_start = datetime.time(6, 0, 0)
    allowed_end   = datetime.time(17, 0, 0)
    if now_time < allowed_start or now_time >= allowed_end:
        messages.error(
            request,
            f"Clock-in is only allowed between 6:00 AM and 5:00 PM. "
            f"Current time is {now_time.strftime('%I:%M %p')}."
        )
        return redirect('my_attendance')

    if request.method == 'POST':
        form = AttendanceClockInForm(request.POST, employee=employee)
        if form.is_valid():
            with transaction.atomic():
                standard_start = datetime.time(8, 0, 0)
                cutoff_time    = datetime.time(17, 0, 0)

                if now_time >= cutoff_time:
                    status = 'absent'
                elif now_time > standard_start:
                    status = 'late'
                else:
                    status = 'present'

                Attendance.objects.create(
                    employee=employee,
                    date=today,
                    time_in=now_time,
                    status=status,
                )

                if status == 'absent':
                    messages.warning(
                        request,
                        f"Clock-in at {now_time.strftime('%I:%M %p')} is after 5:00 PM. "
                        f"Your attendance has been marked as Absent."
                    )
                elif status == 'late':
                    messages.warning(
                        request,
                        f"Clocked in at {now_time.strftime('%I:%M %p')}. You are late today."
                    )
                else:
                    messages.success(
                        request,
                        f"Clocked in at {now_time.strftime('%I:%M %p')}. Have a productive day!"
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
                    time_out_dt    = datetime.datetime.combine(today, now_time)
                    std_end_dt     = datetime.datetime.combine(today, standard_end)
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

    yesterday = today - datetime.timedelta(days=1)
    if yesterday.weekday() < 5:
        auto_mark_absent_for_date(yesterday)

    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year,
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

    yesterday = today - datetime.timedelta(days=1)
    if yesterday.weekday() < 5:
        auto_mark_absent_for_date(yesterday)

    date_filter = request.GET.get('date', str(today))
    emp_filter  = request.GET.get('employee', '')

    records = Attendance.objects.select_related(
        'employee', 'employee__department'
    ).order_by('-date', 'employee')

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
def run_auto_absent(request):
    if request.method == 'POST':
        days = int(request.POST.get('days', 30))
        total = auto_mark_absent_past_days(days_back=days)
        messages.success(
            request,
            f"Auto-absent complete. {total} absent records created for the past {days} days."
        )
    else:
        total = auto_mark_absent_for_date(get_ph_now().date() - datetime.timedelta(days=1))
        messages.success(
            request,
            f"Auto-absent complete. {total} absent records created for yesterday."
        )
    return redirect('admin_attendance_list')


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


@employee_required
def my_schedule(request):
    employee = request.user.employee_profile
    today = get_ph_now().date()

    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year', today.year))

    yesterday = today - datetime.timedelta(days=1)
    if yesterday.weekday() < 5:
        auto_mark_absent_for_date(yesterday)

    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year,
    )
    att_dict = {att.date: att for att in attendance_records}

    approved_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__lte=datetime.date(year, month, calendar.monthrange(year, month)[1]),
        end_date__gte=datetime.date(year, month, 1),
    )

    leave_dict = {}
    for leave in approved_leaves:
        current = leave.start_date
        while current <= leave.end_date:
            if current.month == month and current.year == year:
                leave_dict[current] = leave
            current += datetime.timedelta(days=1)

    cal = calendar.monthcalendar(year, month)
    month_name = datetime.date(year, month, 1).strftime('%B %Y')

    weeks = []
    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                week_days.append(None)
            else:
                d = datetime.date(year, month, day)
                week_days.append({
                    'date':           d,
                    'day':            day,
                    'is_weekend':     d.weekday() >= 5,
                    'is_today':       d == today,
                    'is_future':      d > today,
                    'before_hired':   d < employee.date_hired,
                    'attendance':     att_dict.get(d),
                    'leave':          leave_dict.get(d),
                })
        weeks.append(week_days)

    context = {
        'employee':        employee,
        'today':           today,
        'month':           month,
        'year':            year,
        'month_name':      month_name,
        'weeks':           weeks,
        'day_names':       ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'months':          [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        'years':           range(today.year - 2, today.year + 1),
        'today_attendance': att_dict.get(today),
    }
    return render(request, 'attendance/my_schedule.html', context)