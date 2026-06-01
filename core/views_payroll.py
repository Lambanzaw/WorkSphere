from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import datetime
import calendar

from .models import Payroll, Employee, Attendance, LeaveRequest, AuditLog
from .forms import PayrollGenerateForm
from .decorators import admin_required, employee_required, get_client_ip


def _compute_sss(basic_salary):
    sss_table = [
        (4250,          135.00),
        (4749,          157.50),
        (5249,          180.00),
        (5749,          202.50),
        (6249,          225.00),
        (6749,          247.50),
        (7249,          270.00),
        (7749,          292.50),
        (8249,          315.00),
        (8749,          337.50),
        (9249,          360.00),
        (9749,          382.50),
        (10249,         405.00),
        (10749,         427.50),
        (11249,         450.00),
        (11749,         472.50),
        (12249,         495.00),
        (12749,         517.50),
        (13249,         540.00),
        (13749,         562.50),
        (14249,         585.00),
        (14749,         607.50),
        (15249,         630.00),
        (15749,         652.50),
        (16249,         675.00),
        (16749,         697.50),
        (17249,         720.00),
        (17749,         742.50),
        (18249,         765.00),
        (18749,         787.50),
        (19249,         810.00),
        (19749,         832.50),
        (20249,         855.00),
        (20749,         877.50),
        (21249,         900.00),
        (21749,         922.50),
        (22249,         945.00),
        (22749,         967.50),
        (23249,         990.00),
        (23749,        1012.50),
        (24249,        1035.00),
        (24749,        1057.50),
        (float('inf'), 1080.00),
    ]
    for ceiling, contribution in sss_table:
        if basic_salary <= ceiling:
            return contribution
    return 1080.00


def _compute_payroll(employee, month, year):
    total_working_days = 0
    first_day = datetime.date(year, month, 1)
    last_day  = datetime.date(year, month, calendar.monthrange(year, month)[1])
    current   = first_day
    while current <= last_day:
        if current.weekday() < 5:
            total_working_days += 1
        current += datetime.timedelta(days=1)

    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year,
    )

    days_worked = attendance_records.filter(
        status__in=['present', 'late', 'overtime', 'half_day']
    ).count()

    approved_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__month=month,
        start_date__year=year,
    )
    approved_leave_days = sum(leave.get_working_days() for leave in approved_leaves)

    days_absent = max(0, total_working_days - days_worked - approved_leave_days)

    total_late_minutes = sum(
        att.get_late_minutes() for att in attendance_records if att.is_late()
    )

    total_overtime_hours = float(sum(
        att.overtime_hours for att in attendance_records
        if att.overtime_approved and att.overtime_hours > 0
    ))

    basic_salary = float(employee.basic_salary)
    daily_rate   = basic_salary / total_working_days if total_working_days > 0 else 0
    hourly_rate  = daily_rate / 8

    absence_deduction = daily_rate * days_absent
    late_deduction    = hourly_rate * (total_late_minutes / 60)
    overtime_pay      = hourly_rate * 1.25 * total_overtime_hours

    sss        = _compute_sss(basic_salary)
    philhealth = round(basic_salary * 0.025, 2)
    pagibig    = round(min(basic_salary * 0.02, 100), 2)

    return {
        'basic_salary':             basic_salary,
        'total_working_days':       total_working_days,
        'days_worked':              days_worked,
        'days_absent':              days_absent,
        'late_minutes':             total_late_minutes,
        'overtime_hours':           total_overtime_hours,
        'absence_deduction':        round(absence_deduction, 2),
        'late_deduction':           round(late_deduction, 2),
        'overtime_pay':             round(overtime_pay, 2),
        'daily_rate':               round(daily_rate, 2),
        'hourly_rate':              round(hourly_rate, 2),
        'sss_contribution':         sss,
        'philhealth_contribution':  philhealth,
        'pagibig_contribution':     pagibig,
    }


@admin_required
def payroll_generate(request):
    if request.method == 'POST':
        form = PayrollGenerateForm(request.POST)
        if form.is_valid():
            employee         = form.cleaned_data['employee']
            month            = int(form.cleaned_data['month'])
            year             = int(form.cleaned_data['year'])
            bonuses          = float(form.cleaned_data.get('bonuses') or 0)
            other_deductions = float(form.cleaned_data.get('other_deductions') or 0)
            tax              = float(form.cleaned_data.get('withholding_tax') or 0)
            notes            = form.cleaned_data.get('notes', '')

            computed = _compute_payroll(employee, month, year)

            sss        = computed['sss_contribution']
            philhealth = computed['philhealth_contribution']
            pagibig    = computed['pagibig_contribution']

            with transaction.atomic():
                total_deductions = (
                    computed['absence_deduction'] +
                    computed['late_deduction']    +
                    sss + philhealth + pagibig + tax +
                    other_deductions
                )
                gross_salary = computed['basic_salary'] + computed['overtime_pay'] + bonuses
                net_salary   = max(0, gross_salary - total_deductions)

                payroll = Payroll.objects.create(
                    employee                = employee,
                    month                   = month,
                    year                    = year,
                    basic_salary            = computed['basic_salary'],
                    days_worked             = computed['days_worked'],
                    days_absent             = computed['days_absent'],
                    late_minutes            = computed['late_minutes'],
                    overtime_hours          = computed['overtime_hours'],
                    absence_deduction       = computed['absence_deduction'],
                    late_deduction          = computed['late_deduction'],
                    sss_contribution        = sss,
                    philhealth_contribution = philhealth,
                    pagibig_contribution    = pagibig,
                    withholding_tax         = tax,
                    other_deductions        = other_deductions,
                    total_deductions        = total_deductions,
                    overtime_pay            = computed['overtime_pay'],
                    bonuses                 = bonuses,
                    gross_salary            = gross_salary,
                    net_salary              = net_salary,
                    status                  = 'draft',
                    generated_by            = request.user,
                    notes                   = notes,
                )

                AuditLog.objects.create(
                    user        = request.user,
                    action      = 'generate_payroll',
                    model_name  = 'Payroll',
                    object_id   = payroll.id,
                    description = (
                        f"Generated payroll for {employee.get_full_name()} — "
                        f"{datetime.date(year, month, 1).strftime('%B %Y')}. "
                        f"Net: ₱{net_salary:,.2f}"
                    ),
                    ip_address  = get_client_ip(request),
                )

                messages.success(
                    request,
                    f"Payroll generated for {employee.get_full_name()} — "
                    f"{datetime.date(year, month, 1).strftime('%B %Y')}. "
                    f"Net salary: ₱{net_salary:,.2f}"
                )
                return redirect('payroll_detail', pk=payroll.pk)
    else:
        form = PayrollGenerateForm(initial={
            'month': timezone.now().month,
            'year':  timezone.now().year,
        })

    return render(request, 'payroll/generate.html', {'form': form})


@admin_required
def payroll_generate_all(request):
    if request.method == 'POST':
        month = int(request.POST.get('month', timezone.now().month))
        year  = int(request.POST.get('year', timezone.now().year))

        employees  = Employee.objects.filter(status='active')
        generated  = 0
        skipped    = 0

        with transaction.atomic():
            for employee in employees:
                if Payroll.objects.filter(employee=employee, month=month, year=year).exists():
                    skipped += 1
                    continue

                computed = _compute_payroll(employee, month, year)

                sss        = computed['sss_contribution']
                philhealth = computed['philhealth_contribution']
                pagibig    = computed['pagibig_contribution']
                tax        = 0
                bonuses    = 0
                other_deductions = 0

                total_deductions = (
                    computed['absence_deduction'] +
                    computed['late_deduction']    +
                    sss + philhealth + pagibig + tax +
                    other_deductions
                )
                gross_salary = computed['basic_salary'] + computed['overtime_pay'] + bonuses
                net_salary   = max(0, gross_salary - total_deductions)

                payroll = Payroll.objects.create(
                    employee                = employee,
                    month                   = month,
                    year                    = year,
                    basic_salary            = computed['basic_salary'],
                    days_worked             = computed['days_worked'],
                    days_absent             = computed['days_absent'],
                    late_minutes            = computed['late_minutes'],
                    overtime_hours          = computed['overtime_hours'],
                    absence_deduction       = computed['absence_deduction'],
                    late_deduction          = computed['late_deduction'],
                    sss_contribution        = sss,
                    philhealth_contribution = philhealth,
                    pagibig_contribution    = pagibig,
                    withholding_tax         = tax,
                    other_deductions        = other_deductions,
                    total_deductions        = total_deductions,
                    overtime_pay            = computed['overtime_pay'],
                    bonuses                 = bonuses,
                    gross_salary            = gross_salary,
                    net_salary              = net_salary,
                    status                  = 'draft',
                    generated_by            = request.user,
                )

                AuditLog.objects.create(
                    user        = request.user,
                    action      = 'generate_payroll',
                    model_name  = 'Payroll',
                    object_id   = payroll.id,
                    description = (
                        f"Bulk generated payroll for {employee.get_full_name()} — "
                        f"{datetime.date(year, month, 1).strftime('%B %Y')}. "
                        f"Net: ₱{net_salary:,.2f}"
                    ),
                    ip_address  = get_client_ip(request),
                )
                generated += 1

        messages.success(
            request,
            f"Bulk payroll complete for {datetime.date(year, month, 1).strftime('%B %Y')}. "
            f"{generated} generated, {skipped} already existed and were skipped."
        )
        return redirect(f'/payroll/?month={month}&year={year}')

    return redirect('payroll_list')


@admin_required
def payroll_list(request):
    today         = timezone.now().date()
    month         = int(request.GET.get('month', today.month))
    year          = int(request.GET.get('year', today.year))
    emp_filter    = request.GET.get('employee', '')
    search_query  = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    selected_month  = request.GET.get('month', str(today.month))
    selected_year   = request.GET.get('year', str(today.year))
    selected_status = request.GET.get('status', '')

    payrolls = Payroll.objects.select_related(
        'employee', 'employee__department'
    ).filter(month=month, year=year).order_by('employee__last_name')

    dept_filter = request.GET.get('department', '')

    if emp_filter:
        payrolls = payrolls.filter(employee_id=emp_filter)
    if search_query:
        payrolls = payrolls.filter(
            employee__first_name__icontains=search_query
        ) | payrolls.filter(
            employee__last_name__icontains=search_query
        ) | payrolls.filter(
            employee__employee_id__icontains=search_query
        ) | payrolls.filter(
            employee__email__icontains=search_query
        )
        payrolls = payrolls.filter(month=month, year=year)
    if dept_filter:
        payrolls = payrolls.filter(employee__department_id=dept_filter)
    if status_filter:
        payrolls = payrolls.filter(status=status_filter)

    from .models import Department
    all_payrolls    = Payroll.objects.all()
    month_total     = sum(p.net_salary for p in payrolls)
    total_count     = all_payrolls.count()
    draft_count     = payrolls.filter(status='draft').count()
    finalized_count = payrolls.filter(status='finalized').count()
    employees       = Employee.objects.filter(status='active').order_by('last_name')
    departments     = Department.objects.all()

    context = {
        'payrolls':        payrolls,
        'month':           month,
        'year':            year,
        'current_month':   month,
        'current_year':    year,
        'month_total':     month_total,
        'total_count':     total_count,
        'draft_count':     draft_count,
        'finalized_count': finalized_count,
        'emp_filter':      emp_filter,
        'search_query':    search_query,
        'dept_filter':     dept_filter,
        'selected_month':  selected_month,
        'selected_year':   selected_year,
        'selected_status': selected_status,
        'employees':       employees,
        'departments':     departments,
        'months':          [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        'years':           range(today.year - 2, today.year + 1),
    }
    
    return render(request, 'payroll/list.html', context)


@admin_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    return render(request, 'payroll/payslip.html', {'payroll': payroll})


@admin_required
def payroll_finalize(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)

    if payroll.status != 'draft':
        messages.warning(request, "This payroll has already been finalized.")
        return redirect('payroll_detail', pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            payroll.status = 'finalized'
            payroll.save()

            AuditLog.objects.create(
                user        = request.user,
                action      = 'update',
                model_name  = 'Payroll',
                object_id   = payroll.id,
                description = f"Finalized payroll for {payroll.employee.get_full_name()} — {payroll.get_month_name()}",
                ip_address  = get_client_ip(request),
            )
            messages.success(request, "Payroll finalized successfully.")
        return redirect('payroll_detail', pk=pk)

    return render(request, 'payroll/finalize_confirm.html', {'payroll': payroll})


@employee_required
def my_payslips(request):
    employee = request.user.employee_profile
    payrolls = Payroll.objects.filter(
        employee=employee,
        status__in=['finalized', 'paid']
    ).order_by('-year', '-month')

    return render(request, 'payroll/my_payslips.html', {'payrolls': payrolls})


@employee_required
def my_payslip_detail(request, pk):
    employee = request.user.employee_profile
    payroll  = get_object_or_404(Payroll, pk=pk, employee=employee)

    if payroll.status == 'draft':
        messages.error(request, "This payslip is not yet available.")
        return redirect('my_payslips')

    return render(request, 'payroll/payslip.html', {'payroll': payroll, 'is_employee_view': True})


import csv
from django.http import HttpResponse

@admin_required
def payroll_export_csv(request):
    """Export payroll records as CSV with active filters applied."""
    today         = timezone.now().date()
    month         = int(request.GET.get('month', today.month))
    year          = int(request.GET.get('year', today.year))
    search_query  = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    payrolls = Payroll.objects.select_related(
        'employee', 'employee__department'
    ).filter(month=month, year=year).order_by('employee__last_name')

    if search_query:
        payrolls = payrolls.filter(
            employee__first_name__icontains=search_query
        ) | payrolls.filter(
            employee__last_name__icontains=search_query
        )
    if status_filter:
        payrolls = payrolls.filter(status=status_filter)

    month_name = datetime.date(year, month, 1).strftime('%B')
    filename   = f"payroll_{month_name}_{year}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Full Name', 'Department', 'Position',
        'Basic Salary', 'Days Worked', 'Days Absent', 'Late Minutes',
        'Overtime Hours', 'Overtime Pay', 'Bonuses',
        'Absence Deduction', 'Late Deduction',
        'SSS', 'PhilHealth', 'Pag-IBIG', 'Withholding Tax',
        'Other Deductions', 'Total Deductions',
        'Gross Salary', 'Net Salary', 'Status', 'Period'
    ])

    for p in payrolls:
        writer.writerow([
            p.employee.employee_id,
            p.employee.get_full_name(),
            p.employee.department.name if p.employee.department else '',
            p.employee.position,
            p.basic_salary,
            p.days_worked,
            p.days_absent,
            p.late_minutes,
            p.overtime_hours,
            p.overtime_pay,
            p.bonuses,
            p.absence_deduction,
            p.late_deduction,
            p.sss_contribution,
            p.philhealth_contribution,
            p.pagibig_contribution,
            p.withholding_tax,
            p.other_deductions,
            p.total_deductions,
            p.gross_salary,
            p.net_salary,
            p.status.title(),
            p.get_month_name(),
        ])

    return response