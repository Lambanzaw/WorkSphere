"""
WorkSphere Leave Management Views
HR Rules enforced:
- Cannot file leave for past dates
- Must be filed at least 2 days in advance
- No leave allowed on weekends
- Must check leave balance before approval
- No overlapping leave requests
- Only admin can approve/reject leaves
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import LeaveRequest, LeaveBalance, LeaveType, AuditLog
from .forms import LeaveRequestForm, LeaveReviewForm
from .decorators import admin_required, employee_required, get_client_ip


# ─── EMPLOYEE: FILE LEAVE ──────────────────────────────────────────────────────
@employee_required
def leave_create(request):
    """Employee files a new leave request."""
    employee = request.user.employee_profile
    today = timezone.now().year

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, employee=employee)
        if form.is_valid():
            with transaction.atomic():
                leave = form.save(commit=False)
                leave.employee = employee
                leave.save()

                messages.success(
                    request,
                    f"✅ Leave request submitted for {leave.start_date} to {leave.end_date}. "
                    f"Pending admin approval."
                )
                return redirect('my_leaves')
    else:
        form = LeaveRequestForm(employee=employee)

    # Show current leave balances
    balances = LeaveBalance.objects.filter(
        employee=employee,
        year=timezone.now().year
    ).select_related('leave_type')

    return render(request, 'leave/create.html', {
        'form': form,
        'balances': balances,
    })


# ─── EMPLOYEE: MY LEAVES ───────────────────────────────────────────────────────
@employee_required
def my_leaves(request):
    """Employee views their leave requests."""
    employee = request.user.employee_profile

    status_filter = request.GET.get('status', '')
    leaves = LeaveRequest.objects.filter(employee=employee).select_related('leave_type')

    if status_filter:
        leaves = leaves.filter(status=status_filter)

    leaves = leaves.order_by('-filed_on')

    # Leave balances for current year
    balances = LeaveBalance.objects.filter(
        employee=employee,
        year=timezone.now().year
    ).select_related('leave_type')

    context = {
        'leaves': leaves,
        'balances': balances,
        'status_filter': status_filter,
    }
    return render(request, 'leave/my_leaves.html', context)


# ─── EMPLOYEE: CANCEL LEAVE ────────────────────────────────────────────────────
@employee_required
def leave_cancel(request, pk):
    """Employee cancels a pending leave request."""
    employee = request.user.employee_profile
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=employee)

    if leave.status != 'pending':
        messages.error(request, "Only pending leave requests can be cancelled.")
        return redirect('my_leaves')

    if request.method == 'POST':
        with transaction.atomic():
            leave.status = 'cancelled'
            leave.save()
            messages.success(request, "Leave request cancelled successfully.")
        return redirect('my_leaves')

    return render(request, 'leave/cancel_confirm.html', {'leave': leave})


# ─── ADMIN: ALL LEAVE REQUESTS ─────────────────────────────────────────────────
@admin_required
def admin_leave_list(request):
    status_filter = request.GET.get('status', 'pending')
    search_query  = request.GET.get('q', '')
    selected_type = request.GET.get('leave_type', '')

    leaves = LeaveRequest.objects.select_related(
        'employee', 'employee__department', 'leave_type'
    ).order_by('-filed_on')

    if status_filter and status_filter != 'all':
        leaves = leaves.filter(status=status_filter)
    if search_query:
        leaves = leaves.filter(employee__user__first_name__icontains=search_query) | \
                 leaves.filter(employee__user__last_name__icontains=search_query)
    if selected_type:
        leaves = leaves.filter(leave_type__pk=selected_type)

    counts = {
        'pending':  LeaveRequest.objects.filter(status='pending').count(),
        'approved': LeaveRequest.objects.filter(status='approved').count(),
        'rejected': LeaveRequest.objects.filter(status='rejected').count(),
    }

    tabs = [
        ('pending',   'Pending',   '⏳'),
        ('approved',  'Approved',  '✅'),
        ('rejected',  'Rejected',  '❌'),
        ('cancelled', 'Cancelled', '🚫'),
        ('all',       'All',       '📋'),
    ]

    context = {
        'leaves':        leaves,
        'status_filter': status_filter,
        'search_query':  search_query,
        'selected_type': selected_type,
        'counts':        counts,
        'leave_types':   LeaveType.objects.all(),
        'tabs':          tabs,
    }
    return render(request, 'leave/admin_list.html', context)


# ─── ADMIN: REVIEW LEAVE ──────────────────────────────────────────────────────
@admin_required
def admin_leave_review(request, pk):
    """
    Admin approves or rejects a leave request.
    HR Rule: Only admin can approve/reject leaves.
    HR Rule: Must check leave balance before approval.
    """
    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.status != 'pending':
        messages.warning(request, "This leave request has already been reviewed.")
        return redirect('admin_leave_list')

    if request.method == 'POST':
        form = LeaveReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data.get('remarks', '')

            with transaction.atomic():
                if action == 'approved':
                    # HR Rule: Check leave balance before approval
                    working_days = leave.get_working_days()
                    try:
                        balance = LeaveBalance.objects.select_for_update().get(
                            employee=leave.employee,
                            leave_type=leave.leave_type,
                            year=leave.start_date.year
                        )
                        if working_days > balance.remaining_days:
                            messages.error(
                                request,
                                f"Cannot approve: {leave.employee.get_full_name()} only has "
                                f"{balance.remaining_days} day(s) remaining for {leave.leave_type.name}. "
                                f"Requested: {working_days} day(s)."
                            )
                            return redirect('admin_leave_review', pk=pk)

                        # Deduct leave balance
                        balance.used_days += working_days
                        balance.save()

                    except LeaveBalance.DoesNotExist:
                        messages.error(request, "No leave balance record found for this employee.")
                        return redirect('admin_leave_review', pk=pk)

                leave.status = action
                leave.admin_remarks = remarks
                leave.reviewed_by = request.user
                leave.reviewed_on = timezone.now()
                leave.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    model_name='LeaveRequest',
                    object_id=leave.id,
                    description=(
                        f"Admin {action} leave request for {leave.employee.get_full_name()} "
                        f"({leave.start_date} to {leave.end_date}). "
                        f"Remarks: {remarks}"
                    ),
                    ip_address=get_client_ip(request),
                )

                action_display = "approved" if action == "approved" else "rejected"
                messages.success(
                    request,
                    f"Leave request for {leave.employee.get_full_name()} has been {action_display}."
                )
                return redirect('admin_leave_list')
    else:
        form = LeaveReviewForm()

    working_days = leave.get_working_days()
    try:
        balance = LeaveBalance.objects.get(
            employee=leave.employee,
            leave_type=leave.leave_type,
            year=leave.start_date.year
        )
    except LeaveBalance.DoesNotExist:
        balance = None

    context = {
        'leave': leave,
        'form': form,
        'working_days': working_days,
        'balance': balance,
    }
    return render(request, 'leave/admin_review.html', context)
