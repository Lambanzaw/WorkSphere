import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
import anthropic
import os

from .models import (
    Employee, Attendance, LeaveBalance, LeaveRequest,
    Payroll, Department, SphereLog
)

# Anthropic Client
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

NAV_URLS = {
    'NAV_DASHBOARD':     {'admin': '/admin-dashboard/', 'employee': '/employee/dashboard/'},
    'NAV_ATTENDANCE':    {'admin': '/attendance/',      'employee': '/my-attendance/'},
    'NAV_LEAVE':         {'admin': '/leave/',           'employee': '/my-leaves/'},
    'NAV_PAYROLL':       {'admin': '/payroll/',         'employee': '/my-payslips/'},
    'NAV_PROFILE':       {'admin': '/employees/',       'employee': '/my-profile/'},
    'NAV_EMPLOYEES':     {'admin': '/employees/',       'employee': None},
    'NAV_REPORTS':       {'admin': '/reports/',         'employee': None},
    'NAV_SCHEDULE':      {'admin': None,                'employee': '/my-schedule/'},
    'NAV_CLOCK_IN':      {'admin': '/attendance/clock-in/',  'employee': '/attendance/clock-in/'},
    'NAV_CLOCK_OUT':     {'admin': '/attendance/clock-out/', 'employee': '/attendance/clock-out/'},
    'NAV_ADD_EMPLOYEE':  {'admin': '/employees/create/', 'employee': None},
    'NAV_LOGOUT':        {'admin': '/logout/', 'employee': '/logout/'},
}


def get_hr_context(user):
    today = timezone.now().date()
    now = timezone.now()
    month = today.month
    year = today.year
    is_admin = user.is_staff or user.is_superuser
    context_lines = []

    context_lines.append("=== SYSTEM CONTEXT ===")
    context_lines.append(f"Current date: {today.strftime('%A, %B %d, %Y')}")
    context_lines.append(f"Current time: {now.strftime('%I:%M %p')}")
    context_lines.append(f"Current month: {today.strftime('%B %Y')}")
    context_lines.append(f"Day of week: {today.strftime('%A')}")
    context_lines.append(f"Is weekday: {'Yes' if today.weekday() < 5 else 'No (Weekend)'}")

    if is_admin:
        total_active = Employee.objects.filter(status='active').count()
        total_inactive = Employee.objects.filter(status='inactive').count()
        total_on_leave = Employee.objects.filter(status='on_leave').count()
        total_all = Employee.objects.count()

        context_lines.append("\n=== EMPLOYEE OVERVIEW ===")
        context_lines.append(f"Total employees (all): {total_all}")
        context_lines.append(f"Active employees: {total_active}")
        context_lines.append(f"Inactive employees: {total_inactive}")
        context_lines.append(f"On leave: {total_on_leave}")

        male_count = Employee.objects.filter(status='active', gender='male').count()
        female_count = Employee.objects.filter(status='active', gender='female').count()
        context_lines.append(f"Male employees: {male_count}")
        context_lines.append(f"Female employees: {female_count}")

        context_lines.append("\n=== DEPARTMENT BREAKDOWN ===")
        for dept in Department.objects.all():
            count = Employee.objects.filter(department=dept, status='active').count()
            if count > 0:
                context_lines.append(f"Department '{dept.name}': {count} active employees")

        present_today = Attendance.objects.filter(date=today, status__in=['present', 'late']).count()
        absent_today = Attendance.objects.filter(date=today, status='absent').count()
        late_today = Attendance.objects.filter(date=today, status='late').count()
        overtime_today = Attendance.objects.filter(date=today, status='overtime').count()

        context_lines.append(f"\n=== TODAY'S ATTENDANCE ({today.strftime('%B %d, %Y')}) ===")
        context_lines.append(f"Present today: {present_today}")
        context_lines.append(f"Absent today: {absent_today}")
        context_lines.append(f"Late today: {late_today}")
        context_lines.append(f"Overtime today: {overtime_today}")
        context_lines.append(f"Not yet recorded: {total_active - present_today - absent_today}")

        absents = Attendance.objects.filter(date=today, status='absent').select_related('employee')[:10]
        if absents:
            context_lines.append("\nAbsent employees today:")
            for a in absents:
                context_lines.append(f"  - {a.employee.get_full_name()} ({a.employee.department.name if a.employee.department else 'N/A'})")

        lates = Attendance.objects.filter(date=today, status='late').select_related('employee')[:10]
        if lates:
            context_lines.append("\nLate employees today:")
            for a in lates:
                context_lines.append(f"  - {a.employee.get_full_name()} (time in: {a.time_in.strftime('%I:%M %p') if a.time_in else 'N/A'})")

        presents = Attendance.objects.filter(date=today, status__in=['present', 'late']).select_related('employee')[:10]
        if presents:
            context_lines.append("\nPresent employees today:")
            for a in presents:
                context_lines.append(f"  - {a.employee.get_full_name()} (in: {a.time_in.strftime('%I:%M %p') if a.time_in else 'N/A'}, out: {a.time_out.strftime('%I:%M %p') if a.time_out else 'still in'})")

        month_present = Attendance.objects.filter(date__month=month, date__year=year, status__in=['present', 'late']).count()
        month_absent = Attendance.objects.filter(date__month=month, date__year=year, status='absent').count()
        month_late = Attendance.objects.filter(date__month=month, date__year=year, status='late').count()

        context_lines.append(f"\n=== THIS MONTH ATTENDANCE SUMMARY ({today.strftime('%B %Y')}) ===")
        context_lines.append(f"Total present records: {month_present}")
        context_lines.append(f"Total absent records: {month_absent}")
        context_lines.append(f"Total late records: {month_late}")

        pending_leaves = LeaveRequest.objects.filter(status='pending').select_related('employee', 'leave_type')
        approved_leaves = LeaveRequest.objects.filter(status='approved').count()
        rejected_leaves = LeaveRequest.objects.filter(status='rejected').count()

        context_lines.append("\n=== LEAVE REQUESTS ===")
        context_lines.append(f"Pending leave requests: {pending_leaves.count()}")
        context_lines.append(f"Approved this year: {approved_leaves}")
        context_lines.append(f"Rejected this year: {rejected_leaves}")

        if pending_leaves.exists():
            context_lines.append("\nPending leave details:")
            for lv in pending_leaves[:10]:
                days = lv.get_working_days()
                context_lines.append(f"  - {lv.employee.get_full_name()}: {lv.leave_type.name} | {lv.start_date} to {lv.end_date} ({days} day/s) | Filed: {lv.filed_on.strftime('%b %d')}")

        payrolls = Payroll.objects.filter(month=month, year=year)
        total_net = sum(float(p.net_salary) for p in payrolls)
        total_gross = sum(float(p.gross_salary) for p in payrolls)
        total_deductions = sum(float(p.total_deductions) for p in payrolls)
        draft_count = payrolls.filter(status='draft').count()
        finalized_count = payrolls.filter(status='finalized').count()

        context_lines.append(f"\n=== PAYROLL SUMMARY ({today.strftime('%B %Y')}) ===")
        context_lines.append(f"Total payroll records: {payrolls.count()}")
        context_lines.append(f"Draft: {draft_count}")
        context_lines.append(f"Finalized: {finalized_count}")
        context_lines.append(f"Total gross pay: P{total_gross:,.2f}")
        context_lines.append(f"Total deductions: P{total_deductions:,.2f}")
        context_lines.append(f"Total net pay: P{total_net:,.2f}")
        context_lines.append(f"Employees without payroll this month: {total_active - payrolls.count()}")

        context_lines.append("\n=== ALL ACTIVE EMPLOYEES ===")
        all_emps = Employee.objects.filter(status='active').select_related('department')
        for emp in all_emps:
            context_lines.append(f"  - {emp.get_full_name()} | ID: {emp.employee_id} | PK: {emp.pk} | {emp.position} | {emp.department.name if emp.department else 'N/A'} | {emp.gender} | Hired: {emp.date_hired}")

    else:
        try:
            emp = user.employee_profile
            records = Attendance.objects.filter(employee=emp, date__month=month, date__year=year)
            present_count = records.filter(status__in=['present', 'late']).count()
            absent_count = records.filter(status='absent').count()
            late_count = records.filter(status='late').count()
            overtime_count = records.filter(status='overtime').count()

            today_att = Attendance.objects.filter(employee=emp, date=today).first()
            total_late_mins = sum(a.get_late_minutes() for a in records.filter(status='late'))
            balances = LeaveBalance.objects.filter(employee=emp, year=year).select_related('leave_type')
            payroll = Payroll.objects.filter(employee=emp, month=month, year=year).first()
            latest_payroll = Payroll.objects.filter(employee=emp).order_by('-year', '-month').first()
            all_leaves = LeaveRequest.objects.filter(employee=emp).order_by('-filed_on')
            pending_leaves = all_leaves.filter(status='pending')
            approved_leaves = all_leaves.filter(status='approved')

            context_lines.append("\n=== EMPLOYEE PROFILE ===")
            context_lines.append(f"Full name: {emp.get_full_name()}")
            context_lines.append(f"Employee ID: {emp.employee_id}")
            context_lines.append(f"Position: {emp.position}")
            context_lines.append(f"Department: {emp.department.name if emp.department else 'N/A'}")
            context_lines.append(f"Gender: {emp.gender}")
            context_lines.append(f"Status: {emp.get_status_display()}")
            context_lines.append(f"Date hired: {emp.date_hired.strftime('%B %d, %Y')}")
            context_lines.append(f"Basic salary: P{emp.basic_salary:,.2f}")
            context_lines.append(f"Contact: {emp.contact_number or 'N/A'}")
            context_lines.append(f"Civil status: {emp.get_civil_status_display() if emp.civil_status else 'N/A'}")
            context_lines.append(f"Nationality: {emp.nationality or 'N/A'}")

            context_lines.append("\n=== TODAY'S STATUS ===")
            if today_att:
                context_lines.append(f"Time in: {today_att.time_in.strftime('%I:%M %p') if today_att.time_in else 'Not yet'}")
                context_lines.append(f"Time out: {today_att.time_out.strftime('%I:%M %p') if today_att.time_out else 'Not yet clocked out'}")
                context_lines.append(f"Status: {today_att.get_status_display()}")
                if today_att.time_in and today_att.time_out:
                    context_lines.append(f"Hours worked today: {today_att.get_hours_worked()} hours")
            else:
                context_lines.append("No attendance record for today yet")

            context_lines.append(f"\n=== THIS MONTH ATTENDANCE ({today.strftime('%B %Y')}) ===")
            context_lines.append(f"Present: {present_count} days")
            context_lines.append(f"Absent: {absent_count} days")
            context_lines.append(f"Late: {late_count} times")
            context_lines.append(f"Overtime: {overtime_count} times")
            context_lines.append(f"Total late minutes: {total_late_mins} minutes")

            recent_att = records.order_by('-date')[:7]
            if recent_att:
                context_lines.append("\nRecent attendance (last 7 records):")
                for a in recent_att:
                    context_lines.append(f"  - {a.date.strftime('%b %d (%a)')}: {a.get_status_display()} | In: {a.time_in.strftime('%I:%M %p') if a.time_in else 'N/A'} | Out: {a.time_out.strftime('%I:%M %p') if a.time_out else 'N/A'}")

            context_lines.append(f"\n=== LEAVE BALANCES ({year}) ===")
            for b in balances:
                context_lines.append(f"{b.leave_type.name}: {b.remaining_days} days remaining (used {b.used_days} of {b.allocated_days} allocated)")

            context_lines.append("\n=== PAYROLL ===")
            if payroll:
                context_lines.append(f"This month ({today.strftime('%B %Y')}):")
                context_lines.append(f"  Basic salary: P{payroll.basic_salary:,.2f}")
                context_lines.append(f"  Gross salary: P{payroll.gross_salary:,.2f}")
                context_lines.append(f"  Total deductions: P{payroll.total_deductions:,.2f}")
                context_lines.append(f"  SSS: P{payroll.sss_contribution:,.2f}")
                context_lines.append(f"  PhilHealth: P{payroll.philhealth_contribution:,.2f}")
                context_lines.append(f"  Pag-IBIG: P{payroll.pagibig_contribution:,.2f}")
                context_lines.append(f"  Net pay: P{payroll.net_salary:,.2f}")
                context_lines.append(f"  Days worked: {payroll.days_worked}")
                context_lines.append(f"  Status: {payroll.status.title()}")
            else:
                context_lines.append("No payroll generated for this month yet.")

            if latest_payroll and latest_payroll != payroll:
                context_lines.append(f"Latest payslip: {latest_payroll.get_month_name()} - Net Pay P{latest_payroll.net_salary:,.2f}")

            context_lines.append("\n=== LEAVE REQUESTS ===")
            context_lines.append(f"Pending: {pending_leaves.count()}")
            context_lines.append(f"Approved: {approved_leaves.count()}")
            if all_leaves.exists():
                context_lines.append("\nRecent leave requests:")
                for lv in all_leaves[:5]:
                    days = lv.get_working_days()
                    context_lines.append(f"  - {lv.leave_type.name}: {lv.start_date} to {lv.end_date} ({days} day/s) | Status: {lv.status.title()} | Filed: {lv.filed_on.strftime('%b %d, %Y')}")
                    if lv.admin_remarks:
                        context_lines.append(f"    Remarks: {lv.admin_remarks}")

            context_lines.append("\n=== WORK SCHEDULE ===")
            context_lines.append("Work days: Monday to Friday")
            context_lines.append("Work hours: 8:00 AM to 5:00 PM")
            context_lines.append("Late threshold: After 8:00 AM")

        except Exception as e:
            context_lines.append(f"Could not load employee data: {str(e)}")

    return "\n".join(context_lines)


def normalize_numbers(text):
    replacements = {
        'twenty ninth': '29th', 'twenty eighth': '28th', 'twenty seventh': '27th',
        'twenty sixth': '26th', 'twenty fifth': '25th', 'twenty fourth': '24th',
        'twenty third': '23rd', 'twenty second': '22nd', 'twenty first': '21st',
        'thirty first': '31st', 'thirtieth': '30th', 'twentieth': '20th',
        'nineteenth': '19th', 'eighteenth': '18th', 'seventeenth': '17th',
        'sixteenth': '16th', 'fifteenth': '15th', 'fourteenth': '14th',
        'thirteenth': '13th', 'twelfth': '12th', 'eleventh': '11th', 'tenth': '10th',
        'ninth': '9th', 'eighth': '8th', 'seventh': '7th', 'sixth': '6th',
        'fifth': '5th', 'fourth': '4th', 'third': '3rd', 'second': '2nd', 'first': '1st',
        'nineteen': '19', 'eighteen': '18', 'seventeen': '17', 'sixteen': '16',
        'fifteen': '15', 'fourteen': '14', 'thirteen': '13', 'twelve': '12',
        'eleven': '11', 'twenty': '20', 'thirty': '30', 'ten': '10',
        'nine': '9', 'eight': '8', 'seven': '7', 'six': '6', 'five': '5',
        'four': '4', 'three': '3', 'two': '2', 'one': '1', 'zero': '0',
    }
    result = text.lower()
    for word, digit in replacements.items():
        result = result.replace(word, digit)
    return result


def ask_claude(user_message, user, is_admin, form_state=None, current_url=''):
    user_message = normalize_numbers(user_message)
    hr_context = get_hr_context(user)
    role = "HR Administrator" if is_admin else "Employee"

    form_context = ""
    if form_state:
        form_context = (
            "\n=== ACTIVE FORM SESSION ===\n"
            f"Currently filling form: {form_state['form']}\n"
            f"Fields filled so far: {json.dumps(form_state['fields'], indent=2)}\n"
            "Continue asking for the next missing required field one at a time.\n"
            "Do NOT re-ask fields already filled above.\n"
        )

    dashboard_url = '/admin-dashboard/' if is_admin else '/employee/dashboard/'
    attendance_url = '/attendance/' if is_admin else '/attendance/my/'
    leave_url = '/leave/' if is_admin else '/leave/my/'
    payroll_url = '/payroll/' if is_admin else '/my-payslips/'
    leave_request_url = '/leave/' if is_admin else '/leave/request/'

    admin_nav = ""
    if is_admin:
        admin_nav = (
            "- Employee List: /employees/\n"
            "- Reports: /reports/\n"
            "- Add New Employee: /employees/create/\n"
            "- Generate Payroll: /payroll/generate/\n"
            "- Attendance Management: /attendance/\n"
        )

    leave_example = (
        "Sphere: Only employees can file leave requests."
        if is_admin else
        "Sphere: NAVIGATE:/leave/request/|I'll take you to the leave form.\nFILL:leave_request|leave_type=Sick Leave|start_date=2026-07-01|end_date=2026-07-03|reason=Fever"
    )

    system_prompt = (
        f"You are Sphere, an AI HR voice assistant for WorkSphere.\n"
        f"User: {role} - {user.get_full_name() or user.username} (username: {user.username})\n"
        f"Admin: {'Yes' if is_admin else 'No'}\n\n"
        f"=== HR DATA ===\n{hr_context}\n{form_context}\n\n"
        f"=== RESPONSE FORMAT ===\n"
        f"Use these commands in your response:\n"
        f"NAVIGATE:/url/|spoken message\n"
        f"FILL:form_name|field=value\n"
        f"SUBMIT:form_name\n"
        f"CANCEL:form_name\n"
        f"INTENT:INTENT_NAME (always end with this)\n\n"
        f"=== NAVIGATION ===\n"
        f"Dashboard: {dashboard_url}\n"
        f"Attendance: {attendance_url}\n"
        f"Leave all: {leave_url}?status=all\n"
        f"Leave pending: {leave_url}?status=pending\n"
        f"Leave approved: {leave_url}?status=approved\n"
        f"Leave rejected: {leave_url}?status=rejected\n"
        f"Leave cancelled: {leave_url}?status=cancelled\n"
        f"Payroll: {payroll_url}\n"
        f"File Leave: {leave_request_url}\n"
        f"Profile: {'/employees/' if is_admin else '/my-profile/'}\n"
        f"Schedule: /my-schedule/\n"
        f"Clock In: /attendance/clock-in/\n"
        f"Clock Out: /attendance/clock-out/\n"
        f"Logout: /logout/\n"
        + (f"Employees: /employees/\nAdd Employee: /employees/create/\nGenerate Payroll: /payroll/generate/\nReports: /reports/\n" if is_admin else "")
        + f"\n=== FORM FIELDS ===\n"
        f"leave_request: leave_type, start_date(YYYY-MM-DD), end_date(YYYY-MM-DD), reason\n"
        f"add_employee: username, employee_id, password, first_name, last_name, gender(male/female), date_of_birth(YYYY-MM-DD), civil_status(single/married/widowed), nationality, email, contact_number, address, department, position, date_hired(YYYY-MM-DD), basic_salary\n"
        f"generate_payroll: month(1-12), year\n\n"
        f"=== CRITICAL RULES ===\n"
        f"1. Admin CANNOT file leave - redirect to {leave_url} instead\n"
        f"2. Convert spoken dates: 'July 3 2026' -> '2026-07-03'\n"
        f"3. Convert spoken numbers: 'twenty five thousand' -> '25000'\n"
        f"4. 'set X to Y' / 'X is Y' / 'make X Y' = FILL command\n"
        f"5. 'submit'/'save'/'create'/'done'/'finish' = SUBMIT command\n"
        f"6. 'cancel'/'back'/'go back' = CANCEL command\n"
        f"7. For 'view [name]' or 'edit [name]': look up PK from HR data, use /employees/PK/ or /employees/PK/edit/\n"
        f"8. ONLY use NAVIGATE on FIRST form response - subsequent fields use ONLY FILL\n"
        f"9. Guided form flow - ask ONE field at a time\n"
        f"10. add_employee order: username->employee_id->password->first_name->last_name->gender->date_of_birth->civil_status->nationality->email->contact_number->address->department->position->date_hired->basic_salary\n"
        f"11. leave_request order: leave_type->start_date->end_date->reason\n"
        f"12. Never put employee names/IDs in URLs\n\n"
        f"=== EXAMPLES ===\n"
        f"'go to dashboard' -> NAVIGATE:{dashboard_url}|Going to dashboard.\nINTENT:NAV_DASHBOARD\n"
        f"'first name is John' -> FILL:add_employee|first_name=John\nINTENT:FORM_FILL\n"
        f"'salary is 25000' -> FILL:add_employee|basic_salary=25000\nINTENT:FORM_FILL\n"
        f"'date hired May 26 2026' -> FILL:add_employee|date_hired=2026-05-26\nINTENT:FORM_FILL\n"
        f"'create employee' -> SUBMIT:add_employee\nINTENT:FORM_FILL\n"
        f"'view pending leaves' -> NAVIGATE:{leave_url}?status=pending|Opening pending leaves.\nINTENT:NAV_LEAVE\n\n"
        f"Intents: GREETING,HELP,VIEW_ATTENDANCE,FILE_LEAVE,CHECK_LEAVE_BALANCE,VIEW_PAYSLIP,"
        f"NAV_DASHBOARD,NAV_ATTENDANCE,NAV_LEAVE,NAV_PAYROLL,NAV_PROFILE,NAV_SCHEDULE,"
        f"NAV_CLOCK_IN,NAV_CLOCK_OUT,NAV_LOGOUT,FORM_FILL,UNKNOWN\n"
    )
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    full_response = message.content[0].text

    intent = 'UNKNOWN'
    response_text = full_response
    if 'INTENT:' in full_response:
        parts = full_response.split('INTENT:')
        response_text = parts[0].strip()
        intent = parts[1].strip().split()[0] if len(parts) > 1 else 'UNKNOWN'

    navigate_url = None
    fill_data = None
    lines = response_text.split('\n')
    nav_line = None
    fill_line = None
    other_lines = []

    for line in lines:
        if 'NAVIGATE:' in line:
            nav_line = line
        elif line.startswith('FILL:'):
            fill_line = line
        else:
            other_lines.append(line)

    if nav_line:
        nav_part = nav_line[nav_line.index('NAVIGATE:'):].replace('NAVIGATE:', '')
        parts = nav_part.split('|')
        navigate_url = parts[0].strip()
        spoken = parts[1].strip() if len(parts) > 1 else 'Navigating...'
        response_text = ' '.join(other_lines).strip() or spoken

    # Resolve employee name in message to PK for direct navigation
    if is_admin:
        text_lower = user_message.lower()
        is_edit = any(w in text_lower for w in ['edit', 'update', 'modify', 'change profile', 'edit profile', 'click edit'])
        is_view = any(w in text_lower for w in ['view', 'show', 'open', 'see'])

        if is_edit or is_view:
            matched_pk = None

            # Try to match employee name from message
            all_emps = Employee.objects.filter(status='active')
            for emp in all_emps:
                full_name = emp.get_full_name().lower()
                first = emp.first_name.lower()
                last = emp.last_name.lower()
                if full_name in text_lower or (first in text_lower and last in text_lower):
                    matched_pk = emp.pk
                    break

            # If no name in message, extract PK from current URL
            if not matched_pk and current_url:
                import re
                match = re.search(r'/employees/(\d+)/', current_url)
                if match:
                    matched_pk = int(match.group(1))

            if matched_pk:
                if is_edit:
                    navigate_url = f'/employees/{matched_pk}/edit/'
                else:
                    navigate_url = f'/employees/{matched_pk}/'

    if fill_line:
        try:
            fill_parts = fill_line.replace('FILL:', '').split('|')
            form_name = fill_parts[0].strip()
            fields = {}
            for part in fill_parts[1:]:
                if '=' in part:
                    key, val = part.split('=', 1)
                    fields[key.strip()] = val.strip()
            fill_data = {'form': form_name, 'fields': fields}
        except Exception:
            fill_data = None

    # Extract submit command
    submit_form = None
    cancel_form = None
    for line in lines:
        if line.startswith('SUBMIT:'):
            submit_form = line.replace('SUBMIT:', '').strip()
        if line.startswith('CANCEL:'):
            cancel_form = line.replace('CANCEL:', '').strip()

    return response_text, intent, navigate_url, fill_data, submit_form, cancel_form


@login_required
def sphere_view(request):
    is_admin = request.user.is_staff or request.user.is_superuser
    logs = SphereLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    return render(request, 'sphere/sphere.html', {
        'is_admin': is_admin,
        'logs': logs,
    })


@login_required
@require_POST
def sphere_chat(request):
    try:
        data = json.loads(request.body)
        text = data.get('message', '').strip()
        is_voice = data.get('is_voice', False)

        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)

        is_admin = request.user.is_staff or request.user.is_superuser
        current_url = data.get('current_url', '')

        form_state = request.session.get('sphere_form_state', None)
        response_text, intent, navigate_url, fill_data, submit_form, cancel_form = ask_claude(
            text, request.user, is_admin, form_state, current_url
        )

        if fill_data:
            if not form_state or form_state.get('form') != fill_data.get('form'):
                request.session['sphere_form_state'] = {
                    'form': fill_data['form'],
                    'fields': dict(fill_data['fields'])
                }
            else:
                existing = request.session.get('sphere_form_state', {'form': fill_data['form'], 'fields': {}})
                existing['fields'].update(fill_data['fields'])
                request.session['sphere_form_state'] = existing
            request.session.modified = True
        elif intent not in ['UNKNOWN', 'GREETING', 'HELP', 'FORM_FILL'] and not fill_data and not navigate_url:
            if 'sphere_form_state' in request.session:
                del request.session['sphere_form_state']

        # Clear form state after submit
        if submit_form:
            if 'sphere_form_state' in request.session:
                del request.session['sphere_form_state']
            request.session.modified = True

        tagalog_words = ['ako', 'ko', 'mo', 'ang', 'ng', 'sa', 'na', 'ba', 'po', 'sino',
                         'ano', 'mag', 'nag', 'mga', 'ito', 'yan', 'dito', 'saan', 'paano',
                         'bakit', 'kailan', 'ilang', 'lahat', 'wala', 'may', 'hindi', 'oo']
        words = text.lower().split()
        language = 'tl' if any(w in tagalog_words for w in words) else 'en'

        SphereLog.objects.create(
            user=request.user,
            role='admin' if is_admin else 'employee',
            transcript=text,
            intent=intent,
            response=response_text,
            language=language,
            is_voice=is_voice,
        )

        return JsonResponse({
            'response': response_text,
            'intent': intent,
            'language': language,
            'navigate_url': navigate_url,
            'fill_data': fill_data,
            'submit_form': submit_form,
            'cancel_form': cancel_form,
        })

    except Exception as e:
        import traceback
        print("SPHERE ERROR:", traceback.format_exc())
        return JsonResponse({
            'response': f'Error: {str(e)}',
            'intent': 'UNKNOWN',
            'language': 'en',
            'navigate_url': None,
            'fill_data': None,
            'submit_form': None,
            'cancel_form': None,
        })

@login_required
def sphere_logs(request):
    if not (request.user.is_staff or request.user.is_superuser):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    logs = SphereLog.objects.all().select_related('user').order_by('-timestamp')[:100]
    return render(request, 'sphere/logs.html', {'logs': logs})