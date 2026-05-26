import json
from django.shortcuts import render
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
    'CHECK_LEAVE_BALANCE': {
        'en': ['leave balance', 'leave credits', 'remaining leave', 'how many leave',
               'leave days', 'vacation leave', 'sick leave', 'leave left'],
        'tl': ['leave balance', 'leave credits', 'natirang leave', 'ilang leave',
               'bakasyon', 'sick leave ko', 'leave ko'],
    },
    'VIEW_ATTENDANCE': {
        'en': ['my attendance', 'attendance record', 'show attendance',
               'view attendance', 'attendance history', 'my record'],
        'tl': ['attendance ko', 'rekord ko', 'ipakita attendance',
               'attendance history', 'rekord ng attendance'],
    },
    'CHECK_ABSENCE': {
        'en': ['absent', 'absences', 'was i absent', 'my absences',
               'how many absent', 'days absent'],
        'tl': ['absent ako', 'absences ko', 'ilang absent', 'absent na araw',
               'naliban ako', 'naliban'],
    },
    'CHECK_LATE': {
        'en': ['late', 'tardiness', 'was i late', 'how many late',
               'late records', 'my late'],
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
               'my position', 'my department', 'my salary'],
        'tl': ['profile ko', 'impormasyon ko', 'posisyon ko',
               'departamento ko', 'sweldo ko'],
    },
    'VIEW_DEPARTMENT_INFO': {
        'en': ['department', 'department head', 'who is the head',
               'department info', 'department members'],
        'tl': ['departamento', 'head ng departamento', 'sino ang head',
               'miyembro ng departamento'],
    },
    'ADMIN_VIEW_ALL_EMPLOYEES': {
        'en': ['all employees', 'list of employees', 'show all employees',
               'how many employees', 'total employees', 'employee list'],
        'tl': ['lahat ng empleyado', 'lista ng empleyado', 'ipakita lahat',
               'ilang empleyado', 'empleyado lahat'],
    },
    'ADMIN_VIEW_ABSENCES': {
        'en': ['who is absent', 'absent today', 'absences today',
               'list absent', 'absent employees', 'who was absent'],
        'tl': ['sino ang absent', 'absent ngayon', 'sino absent',
               'listahan ng absent'],
    },
    'ADMIN_VIEW_LATE': {
        'en': ['who is late', 'late today', 'late employees',
               'who came late', 'tardy today'],
        'tl': ['sino ang late', 'late ngayon', 'sino late',
               'sino ang huli', 'listahan ng late'],
    },
    'ADMIN_VIEW_PRESENT': {
        'en': ['who is present', 'present today', 'present employees',
               'who clocked in', 'attendance today'],
        'tl': ['sino ang present', 'present ngayon', 'sino nakapasok',
               'listahan ng present'],
    },
    'ADMIN_CHECK_PAYROLL': {
        'en': ['payroll', 'salary', 'pay slip', 'net pay',
               'payroll summary', 'employee salary', 'how much salary'],
        'tl': ['payroll', 'sweldo', 'suweldo', 'net pay',
               'payslip', 'magkano sweldo'],
    },
    'ADMIN_GENERATE_REPORT': {
        'en': ['generate report', 'attendance report', 'hr report',
               'monthly report', 'report summary', 'generate'],
        'tl': ['gumawa ng report', 'attendance report', 'buwanang ulat',
               'ulat', 'i-generate'],
    },
    'GREETING': {
        'en': ['hello', 'hi', 'hey', 'good morning', 'good afternoon',
               'good evening', 'greetings'],
        'tl': ['hello', 'hi', 'kumusta', 'magandang umaga',
               'magandang hapon', 'magandang gabi'],
    },
    'HELP': {
        'en': ['help', 'what can you do', 'commands', 'what can i ask',
               'how to use', 'guide'],
        'tl': ['tulong', 'ano magagawa mo', 'paano gamitin', 'guide'],
    },
}


def detect_language(text):
    tagalog_words = [
        'ako', 'ko', 'mo', 'siya', 'kami', 'kayo', 'sila', 'ang', 'ng',
        'sa', 'na', 'ba', 'po', 'opo', 'hindi', 'oo', 'sino', 'ano',
        'saan', 'kailan', 'bakit', 'paano', 'may', 'mga', 'lahat',
        'ngayon', 'kanina', 'bukas', 'kahapon', 'ilang', 'magkano',
        'natin', 'namin', 'nila', 'niya', 'ipakita', 'gumawa', 'sino'
    ]
    words = text.lower().split()
    tagalog_count = sum(1 for w in words if w in tagalog_words)
    return 'tl' if tagalog_count >= 1 else 'en'


def detect_intent(text, is_admin=False):
    text_lower = text.lower()
    best_intent = None
    best_score = 0

    for intent, keywords in INTENTS.items():
        if not is_admin and intent.startswith('ADMIN_'):
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
    year = today.year
    is_admin = user.is_staff or user.is_superuser

    if intent == 'GREETING':
        name = user.get_full_name() or user.username
        if language == 'tl':
            return f"Kumusta, {name}! Ako si Sphere, ang inyong HR assistant. Paano kita matutulungan?"
        return f"Hello, {name}! I'm Sphere, your HR assistant. How can I help you today?"

    if intent == 'HELP':
        if is_admin:
            if language == 'tl':
                return "Maaari akong tumulong sa: lahat ng empleyado, absent ngayon, late ngayon, present ngayon, payroll, at mga ulat."
            return "I can help you with: all employees, absent today, late today, present today, payroll summary, and reports."
        else:
            if language == 'tl':
                return "Maaari akong tumulong sa: leave balance, attendance, absent, late records, schedule, at profile."
            return "I can help you with: leave balance, attendance records, absences, late records, schedule, and your profile."

    if intent == 'CHECK_LEAVE_BALANCE':
        try:
            emp = user.employee_profile
            balances = LeaveBalance.objects.filter(
                employee=emp, year=year
            ).select_related('leave_type').exclude(
                leave_type__name='Maternity Leave' if emp.gender == 'male' else 'Paternity Leave'
            )
            if not balances.exists():
                return "No leave balances found for this year. Please contact HR." if language == 'en' else "Walang leave balance para sa taong ito. Makipag-ugnayan sa HR."
            lines = []
            for b in balances:
                if language == 'tl':
                    lines.append(f"{b.leave_type.name}: {b.remaining_days} araw natitira sa {b.allocated_days}")
                else:
                    lines.append(f"{b.leave_type.name}: {b.remaining_days} days remaining of {b.allocated_days}")
            if language == 'tl':
                return "Narito ang iyong leave balance:\n" + "\n".join(lines)
            return "Here are your leave balances:\n" + "\n".join(lines)
        except:
            return "No employee profile found." if language == 'en' else "Walang employee profile."

    if intent == 'VIEW_ATTENDANCE':
        try:
            emp = user.employee_profile
            records = Attendance.objects.filter(
                employee=emp, date__month=month, date__year=year
            )
            present = records.filter(status__in=['present', 'late']).count()
            absent = records.filter(status='absent').count()
            late = records.filter(status='late').count()
            if language == 'tl':
                return (f"Attendance mo ngayong buwan:\n"
                        f"Present: {present} araw\n"
                        f"Absent: {absent} araw\n"
                        f"Late: {late} beses")
            return (f"Your attendance this month:\n"
                    f"Present: {present} days\n"
                    f"Absent: {absent} days\n"
                    f"Late: {late} times")
        except:
            return "Could not retrieve attendance." if language == 'en' else "Hindi makuha ang attendance."

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

    if intent == 'VIEW_SCHEDULE':
        if language == 'tl':
            return "Ang iyong schedule ay Lunes hanggang Biyernes, 8:00 AM hanggang 5:00 PM."
        return "Your work schedule is Monday to Friday, 8:00 AM to 5:00 PM."

    if intent == 'VIEW_EMPLOYEE_PROFILE':
        try:
            emp = user.employee_profile
            if language == 'tl':
                return (f"Profile mo:\n"
                        f"Pangalan: {emp.get_full_name()}\n"
                        f"ID: {emp.employee_id}\n"
                        f"Posisyon: {emp.position}\n"
                        f"Departamento: {emp.department.name if emp.department else 'N/A'}\n"
                        f"Status: {emp.get_status_display()}")
            return (f"Your profile:\n"
                    f"Name: {emp.get_full_name()}\n"
                    f"ID: {emp.employee_id}\n"
                    f"Position: {emp.position}\n"
                    f"Department: {emp.department.name if emp.department else 'N/A'}\n"
                    f"Status: {emp.get_status_display()}")
        except:
            return "No profile found." if language == 'en' else "Walang profile."

    if intent == 'VIEW_DEPARTMENT_INFO':
        # Check if a specific department is mentioned in the query
        text_lower = text.lower() if 'text' in dir() else ''
        dept_found = None
        for dept in Department.objects.all():
            if dept.name.lower() in text_lower:
                dept_found = dept
                break

        if dept_found:
            members = Employee.objects.filter(
                department=dept_found, status='active'
            ).select_related('user')
            names = [e.get_full_name() for e in members]
            count = members.count()
            if language == 'tl':
                resp = f"Departamento: {dept_found.name}\nBilang ng miyembro: {count}"
                if names:
                    resp += "\nMga miyembro:\n" + "\n".join(f"• {n}" for n in names)
            else:
                resp = f"Department: {dept_found.name}\nActive members: {count}"
                if names:
                    resp += "\nMembers:\n" + "\n".join(f"• {n}" for n in names)
            return resp

        # Fallback for employee checking own department
        try:
            emp = user.employee_profile
            dept = emp.department
            if not dept:
                return "You are not assigned to a department." if language == 'en' else "Wala kang departamento."
            members = Employee.objects.filter(department=dept, status='active')
            names = [e.get_full_name() for e in members]
            count = members.count()
            if language == 'tl':
                resp = f"Departamento: {dept.name}\nBilang ng miyembro: {count}"
                if names:
                    resp += "\nMga miyembro:\n" + "\n".join(f"• {n}" for n in names)
            else:
                resp = f"Department: {dept.name}\nActive members: {count}"
                if names:
                    resp += "\nMembers:\n" + "\n".join(f"• {n}" for n in names)
            return resp
        except:
            return "Could not get department info." if language == 'en' else "Hindi makuha ang department info."

    # ── Admin intents ─────────────────────────────────────────────────────────
    if not is_admin:
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
                lines.append(f"{d.name}: {count}")
        if language == 'tl':
            return f"Kabuuang aktibong empleyado: {total}\n" + "\n".join(lines)
        return f"Total active employees: {total}\n" + "\n".join(lines)

    if intent == 'ADMIN_VIEW_ABSENCES':
        absents = Attendance.objects.filter(
            date=today, status='absent'
        ).select_related('employee')
        count = absents.count()
        names = [a.employee.get_full_name() for a in absents[:5]]
        if language == 'tl':
            resp = f"May {count} empleyado na absent ngayon."
            if names:
                resp += "\nKabilang ang: " + ", ".join(names)
        else:
            resp = f"There are {count} absent employee(s) today."
            if names:
                resp += "\nIncluding: " + ", ".join(names)
        return resp

    if intent == 'ADMIN_VIEW_LATE':
        late_emps = Attendance.objects.filter(
            date=today, status='late'
        ).select_related('employee')
        count = late_emps.count()
        names = [a.employee.get_full_name() for a in late_emps[:5]]
        if language == 'tl':
            resp = f"May {count} empleyado na late ngayon."
            if names:
                resp += "\nKabilang ang: " + ", ".join(names)
        else:
            resp = f"There are {count} late employee(s) today."
            if names:
                resp += "\nIncluding: " + ", ".join(names)
        return resp

    if intent == 'ADMIN_VIEW_PRESENT':
        count = Attendance.objects.filter(
            date=today, status__in=['present', 'late']
        ).count()
        if language == 'tl':
            return f"May {count} empleyado na present ngayon."
        return f"There are {count} present employee(s) today."

    if intent == 'ADMIN_CHECK_PAYROLL':
        payrolls = Payroll.objects.filter(month=month, year=year)
        count = payrolls.count()
        total = sum(float(p.net_salary) for p in payrolls)
        if language == 'tl':
            return (f"Payroll para ngayong buwan:\n"
                    f"Bilang ng records: {count}\n"
                    f"Kabuuang net pay: ₱{total:,.2f}")
        return (f"Payroll for this month:\n"
                f"Records: {count}\n"
                f"Total net pay: ₱{total:,.2f}")

    if intent == 'ADMIN_GENERATE_REPORT':
        total_emp = Employee.objects.filter(status='active').count()
        present = Attendance.objects.filter(date=today, status__in=['present', 'late']).count()
        absent = Attendance.objects.filter(date=today, status='absent').count()
        pending = LeaveRequest.objects.filter(status='pending').count()
        if language == 'tl':
            return (f"HR Summary ngayon:\n"
                    f"Aktibong empleyado: {total_emp}\n"
                    f"Present ngayon: {present}\n"
                    f"Absent ngayon: {absent}\n"
                    f"Pending leaves: {pending}")
        return (f"HR Summary for today:\n"
                f"Active employees: {total_emp}\n"
                f"Present today: {present}\n"
                f"Absent today: {absent}\n"
                f"Pending leave requests: {pending}")

    if language == 'tl':
        return "Hindi ko naintindihan ang iyong tanong. Subukan mo ulit."
    return "I didn't understand that. Please try rephrasing your question."


@login_required
def sphere_view(request):
    from django.shortcuts import redirect
    return redirect('dashboard')


@login_required
@require_POST
def sphere_chat(request):
    from .models import SphereLog
    try:
        data = json.loads(request.body)
        text = data.get('message', '').strip()
        is_voice = data.get('is_voice', False)

        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)

        is_admin = request.user.is_staff or request.user.is_superuser
        language = detect_language(text)
        intent = detect_intent(text, is_admin)
        response = get_response(intent, request.user, language, text)

        SphereLog.objects.create(
            user=request.user,
            role='admin' if is_admin else 'employee',
            transcript=text,
            intent=intent,
            response=response,
            language=language,
            is_voice=is_voice,
        )

        return JsonResponse({
            'response': response,
            'intent': intent,
            'language': language,
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