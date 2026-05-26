from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Sum
import datetime
import json
import pytz

from .models import Employee, Attendance, LeaveRequest, Payroll, Department, AuditLog
from .decorators import admin_required


@admin_required
def reports_index(request):
    ph_tz = pytz.timezone('Asia/Manila')
    today = timezone.now().astimezone(ph_tz).date()

    month       = int(request.GET.get('month', today.month))
    year        = int(request.GET.get('year', today.year))
    report_type = request.GET.get('report', 'attendance')

    total_employees  = Employee.objects.count()
    active_employees = Employee.objects.filter(status='active').count()

    month_attendance = Attendance.objects.filter(date__month=month, date__year=year)
    total_att        = month_attendance.count()
    present_count    = month_attendance.filter(status__in=['present', 'late']).count()
    avg_attendance   = round(present_count / total_att * 100, 1) if total_att > 0 else 0

    leaves_this_month = LeaveRequest.objects.filter(
        status='approved',
        start_date__month=month,
        start_date__year=year
    ).count()

    total_payroll = Payroll.objects.filter(
        month=month, year=year
    ).aggregate(total=Sum('net_salary'))['total'] or 0

    stats = {
        'total_employees':     total_employees,
        'active_employees':    active_employees,
        'avg_attendance_rate': avg_attendance,
        'leaves_this_month':   leaves_this_month,
        'total_payroll':       float(total_payroll),
    }

    # Directory filters
    dir_search = request.GET.get('dir_search', '').strip()
    dir_dept   = request.GET.get('dir_dept', '')
    dir_status = request.GET.get('dir_status', '')

    employee_directory = Employee.objects.select_related('department').order_by(
        'department__name', 'last_name'
    )
    if dir_search:
        employee_directory = employee_directory.filter(
            first_name__icontains=dir_search
        ) | employee_directory.filter(
            last_name__icontains=dir_search
        ) | employee_directory.filter(
            employee_id__icontains=dir_search
        ) | employee_directory.filter(
            position__icontains=dir_search
        )
    if dir_dept:
        employee_directory = employee_directory.filter(department_id=dir_dept)
    if dir_status:
        employee_directory = employee_directory.filter(status=dir_status)

    departments = Department.objects.all()
    att_labels  = []
    att_present = []
    att_absent  = []
    att_late    = []
    dept_stats  = []

    for dept in departments:
        emps = Employee.objects.filter(department=dept)
        if emps.count() == 0:
            continue

        emp_ids  = list(emps.values_list('id', flat=True))
        dept_att = month_attendance.filter(employee_id__in=emp_ids)

        if dept_att.count() == 0:
            continue

        p     = int(dept_att.filter(status__in=['present', 'late']).count())
        a     = int(dept_att.filter(status='absent').count())
        l     = int(dept_att.filter(status='late').count())
        total = p + a
        rate  = round(p / total * 100) if total > 0 else 100

        att_labels.append(dept.name)
        att_present.append(p)
        att_absent.append(a)
        att_late.append(l)

        dept_stats.append({
            'department':      dept.name,
            'employee_count':  emps.count(),
            'present_count':   p,
            'absent_count':    a,
            'late_count':      l,
            'attendance_rate': rate,
        })

    if not att_labels and total_att > 0:
        for rec in month_attendance.select_related('employee', 'employee__department'):
            dept_name = rec.employee.department.name if rec.employee.department else 'No Department'
            if dept_name not in att_labels:
                emp_dept_att = month_attendance.filter(
                    employee__department__name=dept_name
                )
                p = int(emp_dept_att.filter(status__in=['present', 'late']).count())
                a = int(emp_dept_att.filter(status='absent').count())
                l = int(emp_dept_att.filter(status='late').count())
                att_labels.append(dept_name)
                att_present.append(p)
                att_absent.append(a)
                att_late.append(l)

    # Payroll filters
    pay_search = request.GET.get('pay_search', '').strip()
    pay_dept   = request.GET.get('pay_dept', '')
    pay_status = request.GET.get('pay_status', '')

    payroll_summary = Payroll.objects.filter(
        month=month, year=year
    ).select_related('employee', 'employee__department').order_by('employee__last_name')

    if pay_search:
        payroll_summary = payroll_summary.filter(
            employee__first_name__icontains=pay_search
        ) | payroll_summary.filter(
            employee__last_name__icontains=pay_search
        )
    if pay_dept:
        payroll_summary = payroll_summary.filter(employee__department_id=pay_dept)
    if pay_status:
        payroll_summary = payroll_summary.filter(status=pay_status)

    leave_by_type = LeaveRequest.objects.filter(
        status='approved',
        start_date__month=month,
        start_date__year=year
    ).values('leave_type__name').annotate(count=Count('id'))

    leave_type_labels = [x['leave_type__name'] for x in leave_by_type]
    leave_type_data   = [int(x['count']) for x in leave_by_type]

    top_absent = []
    for emp in Employee.objects.filter(status='active').select_related('department'):
        absences = int(month_attendance.filter(employee=emp, status='absent').count())
        if absences > 0:
            top_absent.append({
                'name':     emp.get_full_name(),
                'dept':     emp.department.name if emp.department else '—',
                'absences': absences,
            })
    top_absent = sorted(top_absent, key=lambda x: x['absences'], reverse=True)[:5]

    top_late = []
    for emp in Employee.objects.filter(status='active').select_related('department'):
        late_count = int(month_attendance.filter(employee=emp, status='late').count())
        if late_count > 0:
            top_late.append({
                'name':       emp.get_full_name(),
                'dept':       emp.department.name if emp.department else '—',
                'late_count': late_count,
            })
    top_late = sorted(top_late, key=lambda x: x['late_count'], reverse=True)[:5]

    audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:20]

    months = [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    years  = list(range(today.year - 2, today.year + 2))

    context = {
        'stats':                   stats,
        'selected_month':          month,
        'selected_year':           year,
        'selected_month_name':     datetime.date(year, month, 1).strftime('%B'),
        'months':                  months,
        'years':                   years,
        'dept_stats':              dept_stats,
        'attendance_labels':       json.dumps(att_labels),
        'attendance_present_data': json.dumps(att_present),
        'attendance_absent_data':  json.dumps(att_absent),
        'attendance_late_data':    json.dumps(att_late),
        'leave_type_labels':       json.dumps(leave_type_labels),
        'leave_type_data':         json.dumps(leave_type_data),
        'has_attendance_data':     len(att_labels) > 0,
        'has_leave_data':          len(leave_type_labels) > 0,
        'top_absent':              top_absent,
        'top_late':                top_late,
        'audit_logs':              audit_logs,
        'employee_directory':      employee_directory,
        'payroll_summary':         payroll_summary,
        'report_type':             report_type,
        'dir_search':              dir_search,
        'dir_dept':                dir_dept,
        'dir_status':              dir_status,
        'pay_search':              pay_search,
        'pay_dept':                pay_dept,
        'pay_status':              pay_status,
        'all_departments':         Department.objects.all().order_by('name'),
    }
    return render(request, 'reports/index.html', context)