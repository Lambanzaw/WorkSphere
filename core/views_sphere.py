import json
import os
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from anthropic import Anthropic
from .models import SphereConversation, Employee, Attendance, LeaveRequest, Payroll

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def get_hr_context(user):
    if user.is_staff or user.is_superuser:
        employees = Employee.objects.filter(status='active').select_related('department')
        emp_list = []
        for e in employees[:20]:
            emp_list.append({
                'name': e.get_full_name(),
                'department': e.department.name if e.department else 'N/A',
                'position': e.position,
                'email': e.email,
                'status': e.status,
            })
        pending_leaves = LeaveRequest.objects.filter(status='pending').count()
        total_employees = Employee.objects.filter(status='active').count()
        return f"""
You are Sphere, an AI HR assistant for WorkSphere HRMS.
You are talking to ADMIN/HR Manager: {user.get_full_name() or user.username}.
You have FULL access to all HR data.

Current HR Data:
- Total Active Employees: {total_employees}
- Pending Leave Requests: {pending_leaves}
- Active Employees: {json.dumps(emp_list, indent=2)}

Answer all HR questions professionally and concisely.
Support both English and Tagalog — reply in the same language the user uses.
For Tagalog questions, answer in Tagalog. For English, answer in English.
"""
    else:
        try:
            emp = user.employee_profile
            my_leaves = LeaveRequest.objects.filter(employee=emp).order_by('-filed_on')[:5]
            my_attendance = Attendance.objects.filter(employee=emp).order_by('-date')[:10]
            leave_list = [{'type': l.leave_type.name, 'status': l.status, 'dates': f"{l.start_date} to {l.end_date}"} for l in my_leaves]
            att_list = [{'date': str(a.date), 'status': a.status, 'time_in': str(a.time_in) if a.time_in else 'N/A'} for a in my_attendance]
            return f"""
You are Sphere, an AI HR assistant for WorkSphere HRMS.
You are talking to EMPLOYEE: {emp.get_full_name()}
Employee ID: {emp.employee_id}
Department: {emp.department.name if emp.department else 'N/A'}
Position: {emp.position}

Their Recent Leave Requests: {json.dumps(leave_list)}
Their Recent Attendance: {json.dumps(att_list)}

STRICT RESTRICTIONS:
- ONLY share this employee's own data
- NEVER share other employees' data, salaries, or records
- If asked about other employees or admin-only data, politely refuse
- You CAN answer general HR policy questions

Support English and Tagalog — reply in the same language the user uses.
"""
        except:
            return f"You are Sphere, an AI HR assistant. User: {user.username}. No employee profile found."


@login_required
def sphere_view(request):
    conversations = SphereConversation.objects.filter(
        user=request.user
    ).order_by('timestamp')[:20]
    is_admin = request.user.is_staff or request.user.is_superuser
    return render(request, 'sphere/sphere.html', {
        'conversations': conversations,
        'is_admin': is_admin,
    })


@login_required
@require_POST
def sphere_chat(request):
    try:
        data = json.loads(request.body)
        question = data.get('message', '').strip()
        history = data.get('history', [])

        if not question:
            return JsonResponse({'error': 'Empty message'}, status=400)

        system_context = get_hr_context(request.user)

        messages = []
        for h in history[-6:]:
            if h.get('role') in ['user', 'assistant']:
                messages.append({'role': h['role'], 'content': h['content']})
        messages.append({'role': 'user', 'content': question})

        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            system=system_context,
            messages=messages,
        )

        answer = response.content[0].text

        tagalog_words = ['ano', 'sino', 'saan', 'may', 'mga', 'ko', 'ako', 'ba', 'ng', 'sa', 'po', 'opo', 'hindi', 'oo', 'paano', 'kailan', 'bakit']
        is_tagalog = any(w in question.lower().split() for w in tagalog_words)

        SphereConversation.objects.create(
            user=request.user,
            question=question,
            response=answer,
            language='tl' if is_tagalog else 'en',
            is_voice=data.get('is_voice', False),
        )

        return JsonResponse({'response': answer})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sphere_logs(request):
    if not (request.user.is_staff or request.user.is_superuser):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    logs = SphereConversation.objects.all().select_related('user').order_by('-timestamp')[:100]
    return render(request, 'sphere/logs.html', {'logs': logs})