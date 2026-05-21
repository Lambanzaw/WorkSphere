"""WorkSphere Django Admin Registration"""

from django.contrib import admin
from .models import (
    Employee, Department, Attendance, LeaveRequest,
    LeaveType, LeaveBalance, Payroll, AuditLog, SpecialWorkingDay
)

admin.site.site_header = "WorkSphere Administration"
admin.site.site_title = "WorkSphere Admin"
admin.site.index_title = "HR Management"

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'get_full_name', 'department', 'position', 'status', 'date_hired']
    list_filter = ['status', 'department']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Name'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'time_in', 'time_out', 'status', 'admin_override']
    list_filter = ['status', 'date', 'admin_override']
    search_fields = ['employee__first_name', 'employee__last_name']

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_days']

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'allocated_days', 'used_days', 'remaining_days']
    list_filter = ['year', 'leave_type']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'filed_on']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__first_name', 'employee__last_name']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'basic_salary', 'net_salary', 'status']
    list_filter = ['status', 'month', 'year']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'description']
    list_filter = ['action', 'model_name']
    readonly_fields = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'description', 'ip_address']

@admin.register(SpecialWorkingDay)
class SpecialWorkingDayAdmin(admin.ModelAdmin):
    list_display = ['date', 'reason', 'created_by']
