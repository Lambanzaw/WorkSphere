import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import (
    Employee, Attendance, LeaveBalance, LeaveRequest,
    Payroll, Department
)

# ─── INTENT KEYWORDS ─────────────────────────────────────────────────────────
INTENTS = {
    # ── Navigation ────────────────────────────────────────────────────────────
    'NAV_DASHBOARD': {
        'en': ['open dashboard', 'go to dashboard', 'dashboard', 'home', 'main page'],
        'tl': ['buksan dashboard', 'dashboard', 'home', 'pumunta dashboard'],
    },
    'NAV_ATTENDANCE': {
        'en': ['open attendance', 'go to attendance', 'attendance page', 'view attendance page'],
        'tl': ['buksan attendance', 'pumunta attendance', 'attendance page'],
    },
    'NAV_LEAVE': {
        'en': ['open leave', 'go to leave', 'leave page', 'my leaves', 'leave requests page'],
        'tl': ['buksan leave', 'pumunta leave', 'leave page', 'leaves ko'],
    },
    'NAV_PAYROLL': {
        'en': ['open payroll', 'go to payroll', 'payroll page', 'my payslips'],
        'tl': ['buksan payroll', 'pumunta payroll', 'payslips ko'],
    },
    'NAV_PROFILE': {
        'en': ['open profile', 'go to profile', 'my profile page', 'view profile'],
        'tl': ['buksan profile', 'pumunta profile', 'profile ko'],
    },
    'NAV_EMPLOYEES': {
        'en': ['open employees', 'go to employees', 'employee list page', 'manage employees'],
        'tl': ['buksan employees', 'pumunta employees', 'listahan ng empleyado'],
    },
    'NAV_REPORTS': {
        'en': ['open reports', 'go to reports', 'reports page', 'view reports'],
        'tl': ['buksan reports', 'pumunta reports', 'mga ulat'],
    },
    'NAV_SCHEDULE': {
        'en': ['open schedule', 'go to schedule', 'my schedule page', 'view schedule'],
        'tl': ['buksan schedule', 'pumunta schedule', 'schedule ko'],
    },
    'NAV_CLOCK_IN': {
        'en': ['clock in', 'time in', 'i want to clock in', 'go to clock in'],
        'tl': ['mag time in', 'time in na', 'clock in', 'pumasok na'],
    },
    'NAV_CLOCK_OUT': {
        'en': ['clock out', 'time out', 'i want to clock out', 'go to clock out'],
        'tl': ['mag time out', 'time out na', 'clock out', 'umuwi na'],
    },
    'NAV_ADD_EMPLOYEE': {
        'en': ['add employee', 'create employee', 'new employee', 'register employee'],
        'tl': ['magdagdag ng empleyado', 'bagong empleyado', 'i-add empleyado'],
    },
    'NAV_LOGOUT': {
        'en': ['logout', 'log out', 'sign out', 'exit'],
        'tl': ['mag logout', 'lumabas', 'mag-sign out'],
    },

    # ── Employee intents ───────────────────────────────────────────────────────
    'CHECK_LEAVE_BALANCE': {
        'en': ['leave balance', 'leave credits', 'remaining leave', 'how many leave',
               'leave days', 'vacation leave', 'sick leave', 'leave left'],
        'tl': ['leave balance', 'leave credits', 'natirang leave', 'ilang leave',
               'bakasyon', 'sick leave ko', 'leave ko'],
    },
    'VIEW_ATTENDANCE': {
        'en': ['my attendance', 'attendance record', 'show attendance',
               'view attendance', 'attendance history', 'my record',
               'check attendance', 'did i time in'],
        'tl': ['attendance ko', 'rekord ko', 'ipakita attendance',
               'attendance history', 'nag time in ba ako'],
    },
    'CHECK_ABSENCE': {
        'en': ['absent', 'absences', 'was i absent', 'my absences',
               'how many absent', 'days absent', 'view absences'],
        'tl': ['absent ako', 'absences ko', 'ilang absent', 'absent na araw',
               'naliban ako', 'naliban'],
    },
    'CHECK_LATE': {
        'en': ['late', 'tardiness', 'was i late', 'how many late',
               'late records', 'my late', 'check late', 'am i late'],
        'tl': ['late ako', 'huli ako', 'nalate ako', 'ilang beses late',
               'may late ba ako', 'late ko'],
    },
    'VIEW_SCHEDULE': {
        'en': ['schedule', 'my schedule', 'work schedule', 'shift',
               'what time', 'work hours'],
        'tl': ['schedule ko', 'oras ng trabaho', 'shift ko', 'anong oras'],
    },
    'VIEW_EMPLOYEE_PROFILE': {
        'en': ['my profile', 'my info', 'my details', 'about me',
               'my position', 'my department', 'my salary', 'who am i'],
        'tl': ['profile ko', 'impormasyon ko', 'posisyon ko',
               'departamento ko', 'sweldo ko'],
    },
    'VIEW_PAYSLIP': {
        'en': ['my payslip', 'my salary', 'how much salary', 'net pay',
               'payroll summary', 'view payslip', 'payroll this month'],
        'tl': ['payslip ko', 'sweldo ko', 'magkano sweldo', 'net pay ko',
               'suweldo ko', 'payroll ko'],
    },
    'FILE_LEAVE': {
        'en': ['file leave', 'apply leave', 'request leave', 'file a leave',
               'submit leave', 'i want to file leave', 'leave request form'],
        'tl': ['mag-file ng leave', 'mag-apply leave', 'humiling ng leave',
               'gusto ko mag-leave', 'leave request'],
    },
    'CHECK_LEAVE_STATUS': {
        'en': ['leave status', 'my leave request', 'pending leave',
               'is my leave approved', 'leave application status'],
        'tl': ['status ng leave', 'leave request ko', 'approved na ba leave ko',
               'pending leave ko'],
    },
    'VIEW_DEPARTMENT_INFO': {
        'en': ['department', 'department head', 'who is the head',
               'department info', 'department members'],
        'tl': ['departamento', 'head ng departamento', 'sino ang head',
               'miyembro ng departamento'],
    },

    # ── Admin intents ──────────────────────────────────────────────────────────
    'ADMIN_VIEW_ALL_EMPLOYEES': {
        'en': ['all employees', 'list of employees', 'show all employees',
               'how many employees', 'total employees', 'employee list'],
        'tl': ['lahat ng empleyado', 'lista ng empleyado', 'ipakita lahat',
               'ilang empleyado', 'empleyado lahat'],
    },
    'ADMIN_SEARCH_EMPLOYEE': {
        'en': ['search employee', 'find employee', 'look for employee',
               'who is employee', 'find staff'],
        'tl': ['hanapin empleyado', 'sino si', 'hanap empleyado'],
    },
    'ADMIN_VIEW_ABSENCES': {
        'en': ['who is absent', 'absent today', 'absences today',
               'list absent', 'absent employees', 'who was absent'],
        'tl': ['sino ang absent', 'absent ngayon', 'sino absent',
               'listahan ng absent'],
    },
    'ADMIN_VIEW_LATE': {
        'en': ['who is late', 'late today', 'late employees',
               'who came late', 'tardy today', 'show late employees'],
        'tl': ['sino ang late', 'late ngayon', 'sino late',
               'sino ang huli', 'listahan ng late'],
    },
    'ADMIN_VIEW_PRESENT': {
        'en': ['who is present', 'present today', 'present employees',
               'who clocked in', 'attendance today', 'show present'],
        'tl': ['sino ang present', 'present ngayon', 'sino nakapasok',
               'listahan ng present'],
    },
    'ADMIN_CHECK_PAYROLL': {
        'en': ['payroll summary', 'payroll report', 'total payroll',
               'payroll this month', 'salary summary', 'generate payroll'],
        'tl': ['payroll summary', 'kabuuang sweldo', 'payroll ngayong buwan',
               'i-generate payroll'],
    },
    'ADMIN_PENDING_LEAVES': {
        'en': ['pending leaves', 'pending leave requests', 'leave requests',
               'approve leave', 'reject leave', 'how many pending leaves'],
        'tl': ['pending leaves', 'leave requests', 'ilang pending leave',
               'mag-approve leave', 'mag-reject leave'],
    },
    'ADMIN_GENERATE_REPORT': {
        'en': ['generate report', 'attendance report', 'hr report',
               'monthly report', 'report summary', 'print report',
               'open report', 'view report'],
        'tl': ['gumawa ng report', 'attendance report', 'buwanang ulat',
               'ulat', 'i-generate report', 'i-print report'],
    },
    'ADMIN_DEPT_SUMMARY': {
        'en': ['department summary', 'department breakdown', 'employees per department',
               'how many per department'],
        'tl': ['buod ng departamento', 'empleyado bawat departamento'],
    },

    # ── General ────────────────────────────────────────────────────────────────
    'GREETING': {
        'en': ['hello', 'hi', 'hey', 'good morning', 'good afternoon',
               'good evening', 'greetings'],
        'tl': ['hello', 'hi', 'kumusta', 'magandang umaga',
               'magandang hapon', 'magandang gabi'],
    },
    'HELP': {
        'en': ['help', 'what can you do', 'commands', 'what can i ask',
               'how to use', 'guide', 'what commands'],
        'tl': ['tulong', 'ano magagawa mo', 'paano gamitin', 'guide',
               'anong commands'],
    },
}

# ─── Navigation URL MAP ───────────────────────────────────────────────────────
NAV_URLS = {
    'NAV_DASHBOARD':     {'admin': '/dashboard/', 'employee': '/employee/dashboard/'},
    'NAV_ATTENDANCE':    {'admin': '/attendance/', 'employee': '/my-attendance/'},
    'NAV_LEAVE':         {'admin': '/leave/',      'employee': '/my-leaves/'},
    'NAV_PAYROLL':       {'admin': '/payroll/',    'employee': '/my-payslips/'},
    'NAV_PROFILE':       {'admin': '/employees/',  'employee': '/my-profile/'},
    'NAV_EMPLOYEES':     {'admin': '/employees/',  'employee': None},
    'NAV_REPORTS':       {'admin': '/reports/',    'employee': None},
    'NAV_SCHEDULE':      {'admin': None,           'employee': '/my-schedule/'},
    'NAV_CLOCK_IN':      {'admin': '/attendance/clock-in/', 'employee': '/attendance/clock-in/'},
    'NAV_CLOCK_OUT':     {'admin': '/attendance/clock-out/', 'employee': '/attendance/clock-out/'},
    'NAV_ADD_EMPLOYEE':  {'admin': '/employees/create/', 'employee': None},
    'NAV_LOGOUT':        {'admin': '/logout/', 'employee': '/logout/'},
}


def detect_language(text):
    tagalog_words = [
        'ako', 'ko', 'mo', 'siya', 'kami', 'kayo', 'sila', 'ang', 'ng',
        'sa', 'na', 'ba', 'po', 'opo', 'hindi', 'oo', 'sino', 'ano',
        'saan', 'kailan', 'bakit', 'paano', 'may', 'mga', 'lahat',
        'ngayon', 'kanina', 'bukas', 'kahapon', 'ilang', 'magkano',
        'natin', 'namin', 'nila', 'niya', 'ipakita', 'gumawa', 'sino',
        'buksan', 'pumunta', 'hanapin', 'magdagdag', 'bago', 'lahat',
        'listahan', 'ulat', 'sweldo', 'suweldo', 'empleyado', 'departamento',
        'absent', 'late', 'present', 'leave', 'payroll', 'schedule',
        'attendance', 'profile', 'tulong', 'paano', 'anong', 'lumabas',
        'mag', 'nag', 'i-', 'umuwi', 'pumasok', 'buwan', 'araw'
    ]
    words = text.lower().split()
    tagalog_count = sum(1 for w in words if w in tagalog_words)
    return 'tl' if tagalog_count >= 1 else 'en'


def detect_intent(text, is_admin=False):
    text_lower = text.lower()
    best_intent = None
    best_score = 0

    for intent, keywords in INTENTS.items():
        # Block admin-only intents for employees
        if not is_admin and intent.startswith('ADMIN_'):
            continue
        # Block admin nav for employees
        if not is_admin and intent in ['NAV_EMPLOYEES', 'NAV_REPORTS', 'NAV_ADD_EMPLOYEE']:
            continue

        score = 0
        for lang in ['en', 'tl']:
            for kw in keywords.get(lang, []):
                if kw in text_lower:
                    score += len(kw.split())
        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent if best_score > 0 else 'UNKNOWN'


def get_response(intent, user, language, text=''):
    today = timezone.now().date()
    month = today.month
    year  = today.year
    is_admin = user.is_staff or user.is_superuser
    role = 'admin' if is_admin else 'employee'

    # ── Navigation intents ────────────────────────────────────────────────────
    if intent in NAV_URLS:
        url = NAV_URLS[intent].get(role)
        if url is None:
            if language == 'tl':
                return "Pasensya na, wala kang permiso para ma-access ang page na iyon."
            return "Sorry, you don't have permission to access that page."

        nav_names = {
            'NAV_DASHBOARD':    ('Dashboard', 'Dashboard'),
            'NAV_ATTENDANCE':   ('Attendance page', 'Attendance page'),
            'NAV_LEAVE':        ('Leave page', 'Leave page'),
            'NAV_PAYROLL':      ('Payroll page', 'Payroll page'),
            'NAV_PROFILE':      ('Profile page', 'Profile page'),
            'NAV_EMPLOYEES':    ('Employees page', 'Employees page'),
            'NAV_REPORTS':      ('Reports page', 'Reports page'),
            'NAV_SCHEDULE':     ('Schedule page', 'Schedule page'),
            'NAV_CLOCK_IN':     ('Clock In page', 'Clock In page'),
            'NAV_CLOCK_OUT':    ('Clock Out page', 'Clock Out page'),
            'NAV_ADD_EMPLOYEE': ('Add Employee page', 'Add Employee page'),
            'NAV_LOGOUT':       ('Logging you out', 'Nag-lo-logout'),
        }
        name_en, name_tl = nav_names.get(intent, ('that page', 'page na iyon'))

        if language == 'tl':
            return f"NAVIGATE:{url}|Bubuksan ko ang {name_tl}..."
        return f"NAVIGATE:{url}|Opening {name_en}..."

    # ── Greeting ──────────────────────────────────────────────────────────────
    if intent == 'GREETING':
        name = user.get_full_name() or user.username
        if language == 'tl':
            return f"Kumusta, {name}! Ako si Sphere, ang inyong HR assistant. Paano kita matutulungan?"
        return f"Hello, {name}! I'm Sphere, your HR assistant. How can I help you today?"

    # ── Help ──────────────────────────────────────────────────────────────────
    if intent == 'HELP':
        if is_admin:
            if language == 'tl':
                return ("Mga command na magagamit mo:\n"
                        "• 'lahat ng empleyado' — tingnan ang lahat\n"
                        "• 'sino absent ngayon' — absent list\n"
                        "• 'sino late ngayon' — late list\n"
                        "• 'sino present ngayon' — present list\n"
                        "• 'pending leaves' — leave requests\n"
                        "• 'payroll summary' — payroll ngayong buwan\n"
                        "• 'open reports' — pumunta sa reports\n"
                        "• 'add employee' — magdagdag ng empleyado\n"
                        "• 'open attendance' — attendance page\n"
                        "• 'logout' — mag-sign out")
            return ("Commands you can use:\n"
                    "• 'all employees' — view employee list\n"
                    "• 'who is absent today' — absent list\n"
                    "• 'who is late today' — late list\n"
                    "• 'who is present today' — present list\n"
                    "• 'pending leaves' — leave requests\n"
                    "• 'payroll summary' — payroll this month\n"
                    "• 'open reports' — go to reports\n"
                    "• 'add employee' — create new employee\n"
                    "• 'open attendance' — attendance page\n"
                    "• 'logout' — sign out")
        else:
            if language == 'tl':
                return ("Mga command na magagamit mo:\n"
                        "• 'leave balance' — tingnan ang leave credits\n"
                        "• 'attendance ko' — attendance ngayong buwan\n"
                        "• 'absent ko' — ilang araw absent\n"
                        "• 'late ko' — ilang beses late\n"
                        "• 'profile ko' — personal info\n"
                        "• 'payslip ko' — tingnan ang sweldo\n"
                        "• 'mag-file ng leave' — pumunta sa leave form\n"
                        "• 'leave status' — status ng leave request\n"
                        "• 'clock in' — pumunta sa clock in\n"
                        "• 'schedule ko' — work schedule\n"
                        "• 'logout' — mag-sign out")
            return ("Commands you can use:\n"
                    "• 'leave balance' — check leave credits\n"
                    "• 'my attendance' — attendance this month\n"
                    "• 'my absences' — absent days\n"
                    "• 'my late records' — late count\n"
                    "• 'my profile' — personal info\n"
                    "• 'my payslip' — view salary\n"
                    "• 'file leave' — go to leave request form\n"
                    "• 'leave status' — check leave request status\n"
                    "• 'clock in' — go to clock in\n"
                    "• 'my schedule' — work schedule\n"
                    "• 'logout' — sign out")

    # ── Leave Balance ─────────────────────────────────────────────────────────
    if intent == 'CHECK_LEAVE_BALANCE':
        try:
            emp = user.employee_profile
            balances = LeaveBalance.objects.filter(
                employee=emp, year=year
            ).select_related('leave_type').exclude(
                leave_type__name='Maternity Leave' if emp.gender == 'male' else 'Paternity Leave'
            )
            if not balances.exists():
                if language == 'tl':
                    return "Walang leave balance para sa taong ito. Makipag-ugnayan sa HR."
                return "No leave balances found for this year. Please contact HR."
            lines = []
            for b in balances:
                if language == 'tl':
                    lines.append(f"• {b.leave_type.name}: {b.remaining_days} araw natitira")
                else:
                    lines.append(f"• {b.leave_type.name}: {b.remaining_days} days remaining")
            if language == 'tl':
                return "Narito ang iyong leave balance:\n" + "\n".join(lines)
            return "Here are your leave balances:\n" + "\n".join(lines)
        except:
            return "No employee profile found." if language == 'en' else "Walang employee profile."

    # ── View Attendance ───────────────────────────────────────────────────────
    if intent == 'VIEW_ATTENDANCE':
        try:
            emp = user.employee_profile
            records = Attendance.objects.filter(
                employee=emp, date__month=month, date__year=year
            )
            present = records.filter(status__in=['present', 'late']).count()
            absent  = records.filter(status='absent').count()
            late    = records.filter(status='late').count()
            if language == 'tl':
                return (f"Attendance mo ngayong buwan:\n"
                        f"• Present: {present} araw\n"
                        f"• Absent: {absent} araw\n"
                        f"• Late: {late} beses")
            return (f"Your attendance this month:\n"
                    f"• Present: {present} days\n"
                    f"• Absent: {absent} days\n"
                    f"• Late: {late} times")
        except:
            return "Could not retrieve attendance." if language == 'en' else "Hindi makuha ang attendance."

    # ── Check Absence ─────────────────────────────────────────────────────────
    if intent == 'CHECK_ABSENCE':
        try:
            emp = user.employee_profile
            count = Attendance.objects.filter(
                employee=emp, status='absent',
                date__month=month, date__year=year
            ).count()
            if language == 'tl':
                return f"Mayroon kang {count} araw na absent ngayong buwan."
            return f"You have {count} absent day(s) this month."
        except:
            return "Could not retrieve absences." if language == 'en' else "Hindi makuha ang absences."

    # ── Check Late ────────────────────────────────────────────────────────────
    if intent == 'CHECK_LATE':
        try:
            emp = user.employee_profile
            count = Attendance.objects.filter(
                employee=emp, status='late',
                date__month=month, date__year=year
            ).count()
            if language == 'tl':
                return f"Nag-late ka ng {count} beses ngayong buwan."
            return f"You were late {count} time(s) this month."
        except:
            return "Could not retrieve late records." if language == 'en' else "Hindi makuha ang late records."

    # ── View Schedule ─────────────────────────────────────────────────────────
    if intent == 'VIEW_SCHEDULE':
        if language == 'tl':
            return "Ang iyong schedule ay Lunes hanggang Biyernes, 8:00 AM hanggang 5:00 PM."
        return "Your work schedule is Monday to Friday, 8:00 AM to 5:00 PM."

    # ── View Profile ──────────────────────────────────────────────────────────
    if intent == 'VIEW_EMPLOYEE_PROFILE':
        try:
            emp = user.employee_profile
            if language == 'tl':
                return (f"Profile mo:\n"
                        f"• Pangalan: {emp.get_full_name()}\n"
                        f"• ID: {emp.employee_id}\n"
                        f"• Posisyon: {emp.position}\n"
                        f"• Departamento: {emp.department.name if emp.department else 'N/A'}\n"
                        f"• Status: {emp.get_status_display()}")
            return (f"Your profile:\n"
                    f"• Name: {emp.get_full_name()}\n"
                    f"• ID: {emp.employee_id}\n"
                    f"• Position: {emp.position}\n"
                    f"• Department: {emp.department.name if emp.department else 'N/A'}\n"
                    f"• Status: {emp.get_status_display()}")
        except:
            return "No profile found." if language == 'en' else "Walang profile."

    # ── View Payslip ──────────────────────────────────────────────────────────
    if intent == 'VIEW_PAYSLIP':
        try:
            emp = user.employee_profile
            payroll = Payroll.objects.filter(
                employee=emp, month=month, year=year
            ).first()
            if payroll:
                if language == 'tl':
                    return (f"Payslip mo ngayong buwan:\n"
                            f"• Basic: ₱{payroll.basic_salary:,.2f}\n"
                            f"• Deductions: ₱{payroll.total_deductions:,.2f}\n"
                            f"• Net Pay: ₱{payroll.net_salary:,.2f}\n"
                            f"• Status: {payroll.status.title()}")
                return (f"Your payslip this month:\n"
                        f"• Basic: ₱{payroll.basic_salary:,.2f}\n"
                        f"• Deductions: ₱{payroll.total_deductions:,.2f}\n"
                        f"• Net Pay: ₱{payroll.net_salary:,.2f}\n"
                        f"• Status: {payroll.status.title()}")
            else:
                if language == 'tl':
                    return "Wala pang payslip para ngayong buwan. Makipag-ugnayan sa HR."
                return "No payslip found for this month. Please contact HR."
        except:
            return "Could not retrieve payslip." if language == 'en' else "Hindi makuha ang payslip."

    # ── File Leave ────────────────────────────────────────────────────────────
    if intent == 'FILE_LEAVE':
        if language == 'tl':
            return "NAVIGATE:/my-leaves/create/|Bubuksan ko ang leave request form..."
        return "NAVIGATE:/my-leaves/create/|Opening the leave request form..."

    # ── Check Leave Status ────────────────────────────────────────────────────
    if intent == 'CHECK_LEAVE_STATUS':
        try:
            emp = user.employee_profile
            leaves = LeaveRequest.objects.filter(
                employee=emp
            ).order_by('-created_at')[:3]
            if not leaves.exists():
                if language == 'tl':
                    return "Wala kang leave request."
                return "You have no leave requests."
            lines = []
            for lv in leaves:
                if language == 'tl':
                    lines.append(f"• {lv.leave_type.name} ({lv.start_date} - {lv.end_date}): {lv.get_status_display()}")
                else:
                    lines.append(f"• {lv.leave_type.name} ({lv.start_date} - {lv.end_date}): {lv.get_status_display()}")
            if language == 'tl':
                return "Pinakabagong leave requests mo:\n" + "\n".join(lines)
            return "Your recent leave requests:\n" + "\n".join(lines)
        except:
            return "Could not retrieve leave status." if language == 'en' else "Hindi makuha ang leave status."

    # ── Department Info ───────────────────────────────────────────────────────
    if intent == 'VIEW_DEPARTMENT_INFO':
        text_lower = text.lower()
        dept_found = None
        for dept in Department.objects.all():
            if dept.name.lower() in text_lower:
                dept_found = dept
                break
        if dept_found:
            members = Employee.objects.filter(department=dept_found, status='active')
            names = [e.get_full_name() for e in members]
            count = members.count()
            if language == 'tl':
                resp = f"Departamento: {dept_found.name}\nBilang ng miyembro: {count}"
                if names:
                    resp += "\nMga miyembro:\n" + "\n".join(f"• {n}" for n in names[:5])
            else:
                resp = f"Department: {dept_found.name}\nActive members: {count}"
                if names:
                    resp += "\nMembers:\n" + "\n".join(f"• {n}" for n in names[:5])
            return resp
        try:
            emp = user.employee_profile
            dept = emp.department
            if not dept:
                return "You are not assigned to a department." if language == 'en' else "Wala kang departamento."
            members = Employee.objects.filter(department=dept, status='active')
            names = [e.get_full_name() for e in members]
            count = members.count()
            if language == 'tl':
                resp = f"Departamento mo: {dept.name}\nBilang ng miyembro: {count}"
                if names:
                    resp += "\nMga miyembro:\n" + "\n".join(f"• {n}" for n in names[:5])
            else:
                resp = f"Your department: {dept.name}\nActive members: {count}"
                if names:
                    resp += "\nMembers:\n" + "\n".join(f"• {n}" for n in names[:5])
            return resp
        except:
            return "Could not get department info." if language == 'en' else "Hindi makuha ang department info."

    # ── Admin: View All Employees ─────────────────────────────────────────────
    if not is_admin and intent.startswith('ADMIN_'):
        if language == 'tl':
            return "Pasensya na, wala kang permiso na ma-access ang impormasyong ito."
        return "Sorry, you do not have permission to access this information."

    if intent == 'ADMIN_VIEW_ALL_EMPLOYEES':
        total = Employee.objects.filter(status='active').count()
        depts = Department.objects.all()
        lines = []
        for d in depts:
            count = Employee.objects.filter(department=d, status='active').count()
            if count > 0:
                lines.append(f"• {d.name}: {count}")
        if language == 'tl':
            return f"Kabuuang aktibong empleyado: {total}\n" + "\n".join(lines)
        return f"Total active employees: {total}\n" + "\n".join(lines)

    # ── Admin: Search Employee ────────────────────────────────────────────────
    if intent == 'ADMIN_SEARCH_EMPLOYEE':
        text_lower = text.lower()
        employees = Employee.objects.filter(status='active')
        found = []
        for emp in employees:
            full = emp.get_full_name().lower()
            if any(word in full for word in text_lower.split() if len(word) > 2):
                found.append(emp)
        if found:
            lines = []
            for e in found[:5]:
                lines.append(f"• {e.get_full_name()} — {e.position} ({e.department.name if e.department else 'N/A'})")
            if language == 'tl':
                return "Nahanap:\n" + "\n".join(lines)
            return "Found:\n" + "\n".join(lines)
        if language == 'tl':
            return "Walang nahanap na empleyado."
        return "No employee found matching that name."

    # ── Admin: View Absences ──────────────────────────────────────────────────
    if intent == 'ADMIN_VIEW_ABSENCES':
        absents = Attendance.objects.filter(
            date=today, status='absent'
        ).select_related('employee')
        count = absents.count()
        names = [a.employee.get_full_name() for a in absents[:5]]
        if language == 'tl':
            resp = f"May {count} empleyado na absent ngayon."
            if names:
                resp += "\nKabilang ang:\n" + "\n".join(f"• {n}" for n in names)
        else:
            resp = f"There are {count} absent employee(s) today."
            if names:
                resp += "\nIncluding:\n" + "\n".join(f"• {n}" for n in names)
        return resp

    # ── Admin: View Late ──────────────────────────────────────────────────────
    if intent == 'ADMIN_VIEW_LATE':
        late_emps = Attendance.objects.filter(
            date=today, status='late'
        ).select_related('employee')
        count = late_emps.count()
        names = [a.employee.get_full_name() for a in late_emps[:5]]
        if language == 'tl':
            resp = f"May {count} empleyado na late ngayon."
            if names:
                resp += "\nKabilang ang:\n" + "\n".join(f"• {n}" for n in names)
        else:
            resp = f"There are {count} late employee(s) today."
            if names:
                resp += "\nIncluding:\n" + "\n".join(f"• {n}" for n in names)
        return resp

    # ── Admin: View Present ───────────────────────────────────────────────────
    if intent == 'ADMIN_VIEW_PRESENT':
        present_emps = Attendance.objects.filter(
            date=today, status__in=['present', 'late']
        ).select_related('employee')
        count = present_emps.count()
        names = [a.employee.get_full_name() for a in present_emps[:5]]
        if language == 'tl':
            resp = f"May {count} empleyado na present ngayon."
            if names:
                resp += "\nKabilang ang:\n" + "\n".join(f"• {n}" for n in names)
        else:
            resp = f"There are {count} present employee(s) today."
            if names:
                resp += "\nIncluding:\n" + "\n".join(f"• {n}" for n in names)
        return resp

    # ── Admin: Pending Leaves ─────────────────────────────────────────────────
    if intent == 'ADMIN_PENDING_LEAVES':
        pending = LeaveRequest.objects.filter(status='pending').select_related('employee')
        count = pending.count()
        names = [f"{lv.employee.get_full_name()} ({lv.leave_type.name})" for lv in pending[:5]]
        if language == 'tl':
            resp = f"May {count} pending leave request."
            if names:
                resp += "\nKabilang ang:\n" + "\n".join(f"• {n}" for n in names)
        else:
            resp = f"There are {count} pending leave request(s)."
            if names:
                resp += "\nIncluding:\n" + "\n".join(f"• {n}" for n in names)
        return resp

    # ── Admin: Check Payroll ──────────────────────────────────────────────────
    if intent == 'ADMIN_CHECK_PAYROLL':
        payrolls = Payroll.objects.filter(month=month, year=year)
        count = payrolls.count()
        total = sum(float(p.net_salary) for p in payrolls)
        draft = payrolls.filter(status='draft').count()
        finalized = payrolls.filter(status='finalized').count()
        if language == 'tl':
            return (f"Payroll para ngayong buwan:\n"
                    f"• Kabuuang records: {count}\n"
                    f"• Draft: {draft}\n"
                    f"• Finalized: {finalized}\n"
                    f"• Kabuuang net pay: ₱{total:,.2f}")
        return (f"Payroll for this month:\n"
                f"• Total records: {count}\n"
                f"• Draft: {draft}\n"
                f"• Finalized: {finalized}\n"
                f"• Total net pay: ₱{total:,.2f}")

    # ── Admin: Generate Report ────────────────────────────────────────────────
    if intent == 'ADMIN_GENERATE_REPORT':
        total_emp = Employee.objects.filter(status='active').count()
        present   = Attendance.objects.filter(date=today, status__in=['present', 'late']).count()
        absent    = Attendance.objects.filter(date=today, status='absent').count()
        late      = Attendance.objects.filter(date=today, status='late').count()
        pending   = LeaveRequest.objects.filter(status='pending').count()
        if language == 'tl':
            return (f"HR Summary ngayon:\n"
                    f"• Aktibong empleyado: {total_emp}\n"
                    f"• Present ngayon: {present}\n"
                    f"• Absent ngayon: {absent}\n"
                    f"• Late ngayon: {late}\n"
                    f"• Pending leaves: {pending}\n\n"
                    f"NAVIGATE:/reports/|Bubuksan ko ang reports page...")
        return (f"HR Summary for today:\n"
                f"• Active employees: {total_emp}\n"
                f"• Present today: {present}\n"
                f"• Absent today: {absent}\n"
                f"• Late today: {late}\n"
                f"• Pending leave requests: {pending}\n\n"
                f"NAVIGATE:/reports/|Opening reports page...")

    # ── Admin: Department Summary ─────────────────────────────────────────────
    if intent == 'ADMIN_DEPT_SUMMARY':
        depts = Department.objects.all()
        lines = []
        for d in depts:
            count = Employee.objects.filter(department=d, status='active').count()
            if count > 0:
                lines.append(f"• {d.name}: {count} employees")
        if language == 'tl':
            return "Bilang ng empleyado bawat departamento:\n" + "\n".join(lines)
        return "Employees per department:\n" + "\n".join(lines)

    # ── Unknown ───────────────────────────────────────────────────────────────
    if language == 'tl':
        return ("Hindi ko naintindihan ang iyong tanong.\n"
                "Subukan mo ang: 'tulong' para sa listahan ng commands.")
    return ("I didn't understand that. Try saying 'help' for a list of commands.")


@login_required
def sphere_view(request):
    is_admin = request.user.is_staff or request.user.is_superuser
    if is_admin:
        return redirect('admin_dashboard')
    return redirect('employee_dashboard')


@login_required
@require_POST
def sphere_chat(request):
    from .models import SphereLog
    try:
        data     = json.loads(request.body)
        text     = data.get('message', '').strip()
        is_voice = data.get('is_voice', False)

        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)

        is_admin = request.user.is_staff or request.user.is_superuser
        language = detect_language(text)
        intent   = detect_intent(text, is_admin)
        response = get_response(intent, request.user, language, text)

        # Handle navigation responses
        navigate_url = None
        display_response = response
        if response.startswith('NAVIGATE:'):
            parts = response.replace('NAVIGATE:', '').split('|')
            navigate_url     = parts[0]
            display_response = parts[1] if len(parts) > 1 else 'Navigating...'

        SphereLog.objects.create(
            user=request.user,
            role='admin' if is_admin else 'employee',
            transcript=text,
            intent=intent,
            response=display_response,
            language=language,
            is_voice=is_voice,
        )

        return JsonResponse({
            'response':     display_response,
            'intent':       intent,
            'language':     language,
            'navigate_url': navigate_url,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sphere_logs(request):
    if not (request.user.is_staff or request.user.is_superuser):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    from .models import SphereLog
    logs = SphereLog.objects.all().select_related('user').order_by('-timestamp')[:100]
    return render(request, 'sphere/logs.html', {'logs': logs})