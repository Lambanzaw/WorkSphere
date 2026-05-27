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
import re


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
        cleaned = super().clean()
        if cleaned.get('username'):
            cleaned['username'] = cleaned['username'].strip()
        return cleaned


# ─── PHONE VALIDATOR ───────────────────────────────────────────────────────────
def validate_ph_phone(number):
    if not number:
        return number
    cleaned = re.sub(r'[\s\-]', '', number)
    if not re.match(r'^(09\d{9}|(\+63)9\d{9})$', cleaned):
        raise forms.ValidationError(
            "Enter a valid Philippine mobile number (e.g. 09171234567 or +639171234567)."
        )
    return cleaned


# ─── EMPLOYEE FORMS ────────────────────────────────────────────────────────────
class EmployeeCreateForm(forms.ModelForm):
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
            'department', 'position', 'gender', 'date_of_birth',
            'civil_status', 'nationality', 'date_hired', 'basic_salary',
            'contact_number', 'address', 'photo', 'status'
        ]
        widgets = {
            'employee_id':    forms.TextInput(attrs={'class': 'form-control'}),
            'first_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':      forms.TextInput(attrs={'class': 'form-control'}),
            'email':          forms.EmailInput(attrs={'class': 'form-control'}),
            'department':     forms.Select(attrs={'class': 'form-select'}),
            'position':       forms.TextInput(attrs={'class': 'form-control'}),
            'gender':         forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'civil_status':   forms.Select(attrs={'class': 'form-select'}),
            'nationality':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Filipino'}),
            'date_hired':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex.09171234567'
            }),
            'address':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo':          forms.FileInput(attrs={'class': 'form-control'}),
            'status':         forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm_password = cleaned.get('confirm_password')
        username = cleaned.get('username')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

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

    def clean_contact_number(self):
        return validate_ph_phone(self.cleaned_data.get('contact_number'))

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if not re.match(r'^[a-zA-Z\s\-\.]+$', name):
            raise forms.ValidationError("First name must contain letters only.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if not re.match(r'^[a-zA-Z\s\-\.]+$', name):
            raise forms.ValidationError("Last name must contain letters only.")
        return name

    def clean_basic_salary(self):
        salary = self.cleaned_data.get('basic_salary')
        if salary is not None and salary < 0:
            raise forms.ValidationError("Basic salary cannot be negative.")
        return salary


class EmployeeEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'email', 'department', 'position',
            'gender', 'date_of_birth', 'civil_status', 'nationality',
            'date_hired', 'basic_salary', 'contact_number',
            'address', 'status', 'photo'
        ]
        widgets = {
            'first_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':      forms.TextInput(attrs={'class': 'form-control'}),
            'email':          forms.EmailInput(attrs={'class': 'form-control'}),
            'department':     forms.Select(attrs={'class': 'form-select'}),
            'position':       forms.TextInput(attrs={'class': 'form-control'}),
            'gender':         forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'civil_status':   forms.Select(attrs={'class': 'form-select'}),
            'nationality':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Filipino'}),
            'date_hired':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09171234567 or +639171234567'
            }),
            'address':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status':         forms.Select(attrs={'class': 'form-select'}),
            'photo':          forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Employee.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered to another employee.")
        return email

    def clean_contact_number(self):
        return validate_ph_phone(self.cleaned_data.get('contact_number'))

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if not re.match(r'^[a-zA-Z\s\-\.]+$', name):
            raise forms.ValidationError("First name must contain letters only.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if not re.match(r'^[a-zA-Z\s\-\.]+$', name):
            raise forms.ValidationError("Last name must contain letters only.")
        return name

    def clean_basic_salary(self):
        salary = self.cleaned_data.get('basic_salary')
        if salary is not None and salary < 0:
            raise forms.ValidationError("Basic salary cannot be negative.")
        return salary


# ─── ATTENDANCE FORMS ──────────────────────────────────────────────────────────
class AttendanceClockInForm(forms.Form):
    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        today = timezone.now().date()

        if today.weekday() >= 5:
            from .models import SpecialWorkingDay
            if not SpecialWorkingDay.objects.filter(date=today).exists():
                raise forms.ValidationError(
                    "Attendance cannot be recorded on weekends (Saturday/Sunday) "
                    "unless it's a designated special working day."
                )

        if self.employee:
            if today < self.employee.date_hired:
                raise forms.ValidationError(
                    f"You cannot clock in before your official hire date "
                    f"({self.employee.date_hired.strftime('%B %d, %Y')})."
                )

            if Attendance.objects.filter(employee=self.employee, date=today).exists():
                raise forms.ValidationError(
                    "You have already clocked in today. Only one attendance record per day is allowed."
                )

        return cleaned


class AttendanceClockOutForm(forms.Form):
    def __init__(self, *args, attendance=None, **kwargs):
        self.attendance = attendance
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        current_time = timezone.now().time()

        if self.attendance and self.attendance.time_in:
            if current_time <= self.attendance.time_in:
                raise forms.ValidationError(
                    "Time-out cannot be earlier than or equal to your time-in."
                )

        return cleaned


class AttendanceAdminForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'time_in', 'time_out', 'status',
                  'overtime_hours', 'overtime_approved', 'admin_override',
                  'override_reason', 'notes']
        widgets = {
            'employee':        forms.Select(attrs={'class': 'form-select'}),
            'date':            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_in':         forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'time_out':        forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status':          forms.Select(attrs={'class': 'form-select'}),
            'overtime_hours':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'override_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes':           forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# ─── LEAVE FORMS ───────────────────────────────────────────────────────────────
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason':     forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Please provide a reason for your leave request...'
            }),
        }

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

        if self.employee:
            if self.employee.gender == 'male':
                self.fields['leave_type'].queryset = LeaveType.objects.exclude(
                    name='Maternity Leave'
                )
            elif self.employee.gender == 'female':
                self.fields['leave_type'].queryset = LeaveType.objects.exclude(
                    name='Paternity Leave'
                )

    def clean(self):
        cleaned = super().clean()
        today = timezone.now().date()
        start_date = cleaned.get('start_date')
        end_date   = cleaned.get('end_date')
        leave_type = cleaned.get('leave_type')

        if leave_type and self.employee:
            if leave_type.name == 'Maternity Leave' and self.employee.gender != 'female':
                raise forms.ValidationError(
                    "Maternity Leave is only available for female employees."
                )
            if leave_type.name == 'Paternity Leave' and self.employee.gender != 'male':
                raise forms.ValidationError(
                    "Paternity Leave is only available for male employees."
                )
            if leave_type.name == 'Maternity Leave' and start_date:
                already_filed = LeaveRequest.objects.filter(
                    employee=self.employee,
                    leave_type=leave_type,
                    status__in=['pending', 'approved'],
                    start_date__year=start_date.year,
                )
                if self.instance.pk:
                    already_filed = already_filed.exclude(pk=self.instance.pk)
                if already_filed.exists():
                    raise forms.ValidationError(
                        f"You have already filed a Maternity Leave request for {start_date.year}. "
                        f"Maternity Leave can only be filed once per year."
                    )
            if leave_type.name == 'Paternity Leave' and start_date:
                already_filed = LeaveRequest.objects.filter(
                    employee=self.employee,
                    leave_type=leave_type,
                    status__in=['pending', 'approved'],
                    start_date__year=start_date.year,
                )
                if self.instance.pk:
                    already_filed = already_filed.exclude(pk=self.instance.pk)
                if already_filed.exists():
                    raise forms.ValidationError(
                        f"You have already filed a Paternity Leave request for {start_date.year}. "
                        f"Paternity Leave can only be filed once per year."
                    )

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError(
                    "Start date must be before or on the same day as end date."
                )
            if start_date < today:
                raise forms.ValidationError(
                    "You cannot file a leave request for past dates."
                )
            advance_days = (start_date - today).days
            if advance_days < 2:
                raise forms.ValidationError(
                    f"Leave request must be filed at least 2 calendar days in advance. "
                    f"Your start date is only {advance_days} day(s) away."
                )
            if start_date.weekday() >= 5:
                raise forms.ValidationError(
                    "Leave start date cannot fall on a weekend (Saturday/Sunday)."
                )
            if end_date.weekday() >= 5:
                raise forms.ValidationError(
                    "Leave end date cannot fall on a weekend (Saturday/Sunday)."
                )
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
                        "You already have a pending or approved leave request "
                        "that overlaps with these dates."
                    )
            if leave_type and self.employee:
                year = start_date.year
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
                            f"Insufficient leave balance. You have {balance.remaining_days} "
                            f"day(s) remaining for {leave_type.name}, but you're requesting "
                            f"{working_days} day(s)."
                        )
                except LeaveBalance.DoesNotExist:
                    raise forms.ValidationError(
                        f"No leave balance allocated for {leave_type.name} in {year}. "
                        f"Please contact HR."
                    )

        return cleaned


class LeaveReviewForm(forms.Form):
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
        required=False, initial=0, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    other_deductions = forms.DecimalField(
        required=False, initial=0, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean(self):
        cleaned = super().clean()
        employee = cleaned.get('employee')
        month    = cleaned.get('month')
        year     = cleaned.get('year')

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
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if Department.objects.filter(name__iexact=name).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name


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