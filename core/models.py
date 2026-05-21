"""
WorkSphere Models
PostgreSQL-backed models with strict HR constraints, NOT NULL, UNIQUE, and CHECK constraints.
All payroll and attendance use database-level integrity via transactions.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime


# ─── DEPARTMENT ────────────────────────────────────────────────────────────────
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ─── EMPLOYEE ──────────────────────────────────────────────────────────────────
class Employee(models.Model):
    """
    HR Rule: Only active employees can log in.
    HR Rule: Unique employee ID and email required.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=20, unique=True)  # UNIQUE constraint
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)  # UNIQUE constraint
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],  # CHECK: salary >= 0
    )
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.employee_id} — {self.get_full_name()}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return self.status == 'active'


# ─── LEAVE TYPE ────────────────────────────────────────────────────────────────
class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_days = models.IntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ─── LEAVE BALANCE ─────────────────────────────────────────────────────────────
class LeaveBalance(models.Model):
    """Tracks remaining leave days per employee per type per year."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    allocated_days = models.IntegerField(default=0)
    used_days = models.IntegerField(default=0)

    class Meta:
        unique_together = ['employee', 'leave_type', 'year']

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days

    def __str__(self):
        return f"{self.employee} — {self.leave_type} ({self.year}): {self.remaining_days} remaining"


# ─── LEAVE REQUEST ─────────────────────────────────────────────────────────────
class LeaveRequest(models.Model):
    """
    HR Rules enforced:
    - Cannot file leave for past dates
    - Must be filed at least 2 days in advance
    - No leave allowed on weekends
    - Must check leave balance before approval
    - No overlapping leave requests
    - Start date must be earlier than end date
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_remarks = models.TextField(blank=True)
    filed_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_leaves'
    )
    reviewed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-filed_on']

    def __str__(self):
        return f"{self.employee} — {self.leave_type} ({self.start_date} to {self.end_date})"

    def get_working_days(self):
        """Count working days (Mon–Fri) in the leave period."""
        count = 0
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() < 5:  # Monday=0, Friday=4
                count += 1
            current += datetime.timedelta(days=1)
        return count

    def clean(self):
        """HR Validation Rules for leave requests."""
        today = timezone.now().date()

        # Rule: start_date must be before end_date
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date must be earlier than or equal to end date.")

        # Rule: Cannot file for past dates
        if self.start_date and self.start_date < today:
            raise ValidationError("You cannot file a leave request for past dates.")

        # Rule: Must file at least 2 days in advance
        if self.start_date:
            advance_days = (self.start_date - today).days
            if advance_days < 2:
                raise ValidationError("Leave must be filed at least 2 working days in advance.")

        # Rule: Start date cannot be a weekend
        if self.start_date and self.start_date.weekday() >= 5:
            raise ValidationError("Leave start date cannot be on a weekend (Saturday or Sunday).")

        # Rule: End date cannot be a weekend
        if self.end_date and self.end_date.weekday() >= 5:
            raise ValidationError("Leave end date cannot be on a weekend (Saturday or Sunday).")


# ─── ATTENDANCE ────────────────────────────────────────────────────────────────
class Attendance(models.Model):
    """
    HR Rules enforced:
    - One time-in per day only
    - Time-out cannot be earlier than time-in
    - No duplicate attendance per day
    - No attendance on weekends
    - Late time-in recorded for deductions
    """
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('absent', 'Absent'),
        ('overtime', 'Overtime'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    overtime_approved = models.BooleanField(default=False)
    admin_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['employee', 'date']  # UNIQUE: no duplicate attendance per day
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} — {self.date} ({self.get_status_display()})"

    def clean(self):
        """HR Attendance Validation Rules."""
        # Rule: No attendance on weekends (unless admin override)
        if self.date and not self.admin_override:
            if self.date.weekday() >= 5:
                raise ValidationError("Attendance cannot be recorded on weekends (Saturday/Sunday).")

        # Rule: Time-out cannot be earlier than time-in
        if self.time_in and self.time_out:
            if self.time_out <= self.time_in:
                raise ValidationError("Time-out cannot be earlier than or equal to time-in.")

    def get_hours_worked(self):
        """Calculate total hours worked."""
        if self.time_in and self.time_out:
            time_in_dt = datetime.datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.datetime.combine(self.date, self.time_out)
            delta = time_out_dt - time_in_dt
            return round(delta.total_seconds() / 3600, 2)
        return 0

    def is_late(self):
        """HR Rule: Standard start time is 8:00 AM. Late if time_in > 08:00."""
        standard_start = datetime.time(8, 0, 0)
        if self.time_in:
            return self.time_in > standard_start
        return False

    def get_late_minutes(self):
        """Calculate how many minutes late."""
        standard_start = datetime.time(8, 0, 0)
        if self.time_in and self.is_late():
            std_dt = datetime.datetime.combine(self.date, standard_start)
            actual_dt = datetime.datetime.combine(self.date, self.time_in)
            delta = actual_dt - std_dt
            return int(delta.total_seconds() / 60)
        return 0


# ─── PAYROLL ───────────────────────────────────────────────────────────────────
class Payroll(models.Model):
    """
    HR Rules enforced:
    - Based only on valid attendance
    - Unapproved absences = no salary
    - Late/absent days = deductions
    - Overtime requires admin approval
    - Salary cannot be negative
    - Payroll is monthly only
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('finalized', 'Finalized'),
        ('paid', 'Paid'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.IntegerField(validators=[MinValueValidator(1)])  # 1–12
    year = models.IntegerField(validators=[MinValueValidator(2000)])
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    days_worked = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    late_minutes = models.IntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Computed deductions
    absence_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
      
      # Government deductions
    sss_contribution    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    philhealth_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pagibig_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    withholding_tax     = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Computed additions
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Final
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]  # CHECK: net salary cannot be negative
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_payrolls')
    generated_on = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'month', 'year']  # One payroll per employee per month
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee} — {self.month}/{self.year} (₱{self.net_salary})"

    def get_month_name(self):
        return datetime.date(self.year, self.month, 1).strftime('%B %Y')


# ─── AUDIT LOG ─────────────────────────────────────────────────────────────────
class AuditLog(models.Model):
    """
    HR Rule: All admin actions must be logged (audit trail).
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('override', 'Override'),
        ('generate_payroll', 'Generate Payroll'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.action} on {self.model_name}"


# ─── SPECIAL WORKING DAY ──────────────────────────────────────────────────────
class SpecialWorkingDay(models.Model):
    """
    HR Rule: No attendance on weekends UNLESS marked as special working day.
    Admin can mark specific weekend dates as working days.
    """
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Special Working Day: {self.date} — {self.reason}"

class AdminSecurityQuestion(models.Model):
    user     = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_question')
    question = models.CharField(max_length=255)
    answer   = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} — security question"