"""
WorkSphere Forms
All forms include backend HR business rule validation.
Input validation on every field — protection against XSS and invalid data.
"""

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Employee, Department, LeaveRequest, LeaveType,
    LeaveBalance, Attendance, Payroll, SpecialWorkingDay
)
import datetime


# ─── AUTHENTICATION FORMS ──────────────────────────────────────────────────────
class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-control',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        """Strip whitespace to prevent XSS injection."""
        cleaned = super().clean()
        if cleaned.get('username'):
            cleaned['username'] = cleaned['username'].strip()
        return cleaned


# ─── EMPLOYEE FORMS ────────────────────────────────────────────────────────────
class EmployeeCreateForm(forms.ModelForm):
    """Form for creating a new employee with linked User account."""
    username = forms.CharField(
        max_length=150,
        help_text="Login username for the employee",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="Minimum 8 characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Employee
        fields = [
            'employee_id', 'first_name', 'last_name', 'email',
            'department', 'position', 'date_hired', 'basic_salary',
            'contact_number', 'address', 'photo', 'status'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'date_hired': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm_password = cleaned.get('confirm_password')
        username = cleaned.get('username')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        # Check unique username
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")

        return cleaned

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Employee.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered to another employee.")
        return email

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id')
        if Employee.objects.filter(employee_id=emp_id).exists():
            raise forms.ValidationError("This Employee ID is already in use.")
        return emp_id


class EmployeeEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'email', 'department', 'position',
            'date_hired', 'basic_salary', 'contact_number', 'address',
            'status', 'photo'
        ]
        widgets = {
            'first_name':       forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':        forms.TextInput(attrs={'class': 'form-control'}),
            'email':            forms.EmailInput(attrs={'class': 'form-control'}),
            'department':       forms.Select(attrs={'class': 'form-select'}),
            'position':         forms.TextInput(attrs={'class': 'form-control'}),
            'date_hired':       forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_number':   forms.TextInput(attrs={'class': 'form-control'}),
            'address':          forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status':           forms.Select(attrs={'class': 'form-select'}),
            'photo':            forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Employee.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered to another employee.")
        return email


# ─── ATTENDANCE FORMS ──────────────────────────────────────────────────────────
class AttendanceClockInForm(forms.Form):
    """Employee clock-in form — validates HR attendance rules."""

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        today = timezone.now().date()

        # HR Rule: No attendance on weekends
        if today.weekday() >= 5:
            # Check if today is a special working day
            from .models import SpecialWorkingDay
            if not SpecialWorkingDay.objects.filter(date=today).exists():
                raise forms.ValidationError(
                    "Attendance cannot be recorded on weekends (Saturday/Sunday) "
                    "unless it's a designated special working day."
                )

        # HR Rule: One time-in per day only
        if self.employee:
            if Attendance.objects.filter(employee=self.employee, date=today).exists():
                raise forms.ValidationError(
                    "You have already clocked in today. Only one attendance record per day is allowed."
                )

        return cleaned


class AttendanceClockOutForm(forms.Form):
    """Employee clock-out form."""

    def __init__(self, *args, attendance=None, **kwargs):
        self.attendance = attendance
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        current_time = timezone.now().time()

        # HR Rule: Time-out cannot be earlier than time-in
        if self.attendance and self.attendance.time_in:
            if current_time <= self.attendance.time_in:
                raise forms.ValidationError(
                    "Time-out cannot be earlier than or equal to your time-in."
                )

        return cleaned


class AttendanceAdminForm(forms.ModelForm):
    """Admin form for override/manual attendance entry."""

    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'time_in', 'time_out', 'status',
                  'overtime_hours', 'overtime_approved', 'admin_override',
                  'override_reason', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'time_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'override_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# ─── LEAVE FORMS ───────────────────────────────────────────────────────────────
class LeaveRequestForm(forms.ModelForm):
    """
    Employee leave request form.
    Enforces all HR leave business rules.
    """

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                           'placeholder': 'Please provide a reason for your leave request...'}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        today = timezone.now().date()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        leave_type = cleaned.get('leave_type')

        if start_date and end_date:
            # HR Rule: Start date must be earlier than end date
            if start_date > end_date:
                raise forms.ValidationError("Start date must be before or on the same day as end date.")

            # HR Rule: Cannot file leave for past dates
            if start_date < today:
                raise forms.ValidationError("You cannot file a leave request for past dates.")

            # HR Rule: Must be filed at least 2 days in advance
            advance_days = (start_date - today).days
            if advance_days < 2:
                raise forms.ValidationError(
                    "Leave request must be filed at least 2 calendar days in advance. "
                    f"Your start date is only {advance_days} day(s) away."
                )

            # HR Rule: No leave on weekends
            if start_date.weekday() >= 5:
                raise forms.ValidationError("Leave start date cannot fall on a weekend (Saturday/Sunday).")

            if end_date.weekday() >= 5:
                raise forms.ValidationError("Leave end date cannot fall on a weekend (Saturday/Sunday).")

            # HR Rule: No overlapping leave requests
            if self.employee:
                overlapping = LeaveRequest.objects.filter(
                    employee=self.employee,
                    status__in=['pending', 'approved'],
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                if self.instance.pk:
                    overlapping = overlapping.exclude(pk=self.instance.pk)
                if overlapping.exists():
                    raise forms.ValidationError(
                        "You already have a pending or approved leave request that overlaps with these dates."
                    )

            # HR Rule: Check leave balance
            if leave_type and self.employee:
                year = start_date.year
                # Count working days requested
                working_days = 0
                current = start_date
                while current <= end_date:
                    if current.weekday() < 5:
                        working_days += 1
                    current += datetime.timedelta(days=1)

                try:
                    balance = LeaveBalance.objects.get(
                        employee=self.employee,
                        leave_type=leave_type,
                        year=year
                    )
                    if working_days > balance.remaining_days:
                        raise forms.ValidationError(
                            f"Insufficient leave balance. You have {balance.remaining_days} day(s) remaining "
                            f"for {leave_type.name}, but you're requesting {working_days} day(s)."
                        )
                except LeaveBalance.DoesNotExist:
                    raise forms.ValidationError(
                        f"No leave balance allocated for {leave_type.name} in {year}. Please contact HR."
                    )

        return cleaned


class LeaveReviewForm(forms.Form):
    """Admin form for approving/rejecting leave requests."""
    action = forms.ChoiceField(
        choices=[('approved', 'Approve'), ('rejected', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional remarks or reason for rejection...'
        })
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get('action')
        remarks = cleaned.get('remarks')
        if action == 'rejected' and not remarks:
            raise forms.ValidationError("Please provide a reason for rejection.")
        return cleaned


# ─── PAYROLL FORMS ─────────────────────────────────────────────────────────────
class PayrollGenerateForm(forms.Form):
    """Admin form to generate monthly payroll."""
    
    sss_contribution = forms.DecimalField(
    required=False, initial=0, min_value=0,
    label='SSS Contribution (₱)',
    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    philhealth_contribution = forms.DecimalField(
    required=False, initial=0, min_value=0,
    label='PhilHealth Contribution (₱)',
    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
)
    pagibig_contribution = forms.DecimalField(
    required=False, initial=0, min_value=0,
    label='Pag-IBIG Contribution (₱)',
    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    withholding_tax = forms.DecimalField(
    required=False, initial=0, min_value=0,
    label='Withholding Tax (₱)',
    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Employee"
    )
    month = forms.ChoiceField(
        choices=[(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    year = forms.IntegerField(
        min_value=2020,
        max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    bonuses = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    other_deductions = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean(self):
        cleaned = super().clean()
        employee = cleaned.get('employee')
        month = cleaned.get('month')
        year = cleaned.get('year')

        if employee and month and year:
            if Payroll.objects.filter(employee=employee, month=month, year=year).exists():
                raise forms.ValidationError(
                    f"Payroll for {employee.get_full_name()} for "
                    f"{datetime.date(year, int(month), 1).strftime('%B %Y')} already exists."
                )
        return cleaned


# ─── DEPARTMENT FORMS ──────────────────────────────────────────────────────────
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email address.")
        return email


SECURITY_QUESTIONS = [
    ('', '-- Select a question --'),
    ('q1', "What is the name of your first pet?"),
    ('q2', "What is your mother's maiden name?"),
    ('q3', "What was the name of your first school?"),
    ('q4', "What is your favorite childhood food?"),
    ('q5', "What city were you born in?"),
]


class SecurityQuestionSetupForm(forms.Form):
    question = forms.ChoiceField(
        choices=SECURITY_QUESTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    answer = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your answer'
        })
    )


class SecurityQuestionVerifyForm(forms.Form):
    answer = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your answer'
        })
    )


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'id': 'new_password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'id': 'confirm_password'
        })
    )

    def clean(self):
        cleaned = super().clean()
        pw  = cleaned.get('new_password', '')
        cpw = cleaned.get('confirm_password', '')

        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")

        import re
        if pw:
            if len(pw) < 8:
                raise forms.ValidationError("Password must be at least 8 characters.")
            if not re.search(r'[A-Z]', pw):
                raise forms.ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[0-9]', pw):
                raise forms.ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', pw):
                raise forms.ValidationError("Password must contain at least one special character.")

        return cleaned