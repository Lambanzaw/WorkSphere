"""
WorkSphere URL Configuration — core app
All routes with role-based access enforced at view level.
"""

from django.urls import path
from . import views_auth, views_employee, views_attendance, views_leave, views_payroll, views_reports

urlpatterns = [
    # ── Authentication ────────────────────────────────────────────────────────
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('dashboard/', views_auth.dashboard_redirect, name='dashboard'),

    path('forgot-password/',        views_auth.forgot_password_email,   name='forgot_password_email'),
    path('forgot-password/verify/', views_auth.forgot_password_verify,  name='forgot_password_verify'),
    path('reset-password/',         views_auth.reset_password,          name='reset_password'),
    path('setup-security-question/', views_auth.setup_security_question, name='setup_security_question'),
    
    # ── Dashboards ────────────────────────────────────────────────────────────
    path('admin-dashboard/', views_employee.admin_dashboard, name='admin_dashboard'),
    path('employee-dashboard/', views_employee.employee_dashboard, name='employee_dashboard'),

    # ── Employee Management (Admin) ───────────────────────────────────────────
    path('employees/', views_employee.employee_list, name='employee_list'),
    path('employees/create/', views_employee.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views_employee.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views_employee.employee_edit, name='employee_edit'),

    # ── Employee Self-Service ─────────────────────────────────────────────────
    path('my-profile/', views_employee.my_profile, name='my_profile'),

    # ── Attendance (Employee) ─────────────────────────────────────────────────
    path('attendance/clock-in/', views_attendance.clock_in, name='clock_in'),
    path('attendance/clock-out/', views_attendance.clock_out, name='clock_out'),
    path('attendance/my/', views_attendance.my_attendance, name='my_attendance'),

    # ── Attendance (Admin) ────────────────────────────────────────────────────
    path('attendance/', views_attendance.admin_attendance_list, name='admin_attendance_list'),
    path('attendance/override/', views_attendance.admin_attendance_override, name='admin_attendance_override'),
    path('attendance/<int:pk>/override/', views_attendance.admin_attendance_override, name='admin_attendance_edit'),

    # ── Leave (Employee) ──────────────────────────────────────────────────────
    path('leave/request/', views_leave.leave_create, name='leave_create'),
    path('leave/my/', views_leave.my_leaves, name='my_leaves'),
    path('leave/<int:pk>/cancel/', views_leave.leave_cancel, name='leave_cancel'),

    # ── Leave (Admin) ─────────────────────────────────────────────────────────
    path('leave/', views_leave.admin_leave_list, name='admin_leave_list'),
    path('leave/<int:pk>/review/', views_leave.admin_leave_review, name='admin_leave_review'),

    # ── Payroll (Admin) ───────────────────────────────────────────────────────
    path('payroll/', views_payroll.payroll_list, name='payroll_list'),
    path('payroll/generate/', views_payroll.payroll_generate, name='payroll_generate'),
    path('payroll/<int:pk>/', views_payroll.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/finalize/', views_payroll.payroll_finalize, name='payroll_finalize'),

    # ── Payroll (Employee) ────────────────────────────────────────────────────
    path('my-payslips/', views_payroll.my_payslips, name='my_payslips'),
    path('my-payslips/<int:pk>/', views_payroll.my_payslip_detail, name='my_payslip_detail'),

    # ── Reports (Admin) ───────────────────────────────────────────────────────
    path('reports/', views_reports.reports_index, name='reports'),
]
