import logging
from datetime import date, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

def auto_mark_absent():
    """
    Runs daily. Marks absent for all active employees
    who have no attendance record for yesterday (Mon-Fri only).
    """
    from .models import Employee, Attendance

    yesterday = timezone.now().date() - timedelta(days=1)

    # Only run for weekdays (Mon=0 to Fri=4)
    if yesterday.weekday() >= 5:
        logger.info(f"Skipping auto-absent for {yesterday} (weekend)")
        return

    active_employees = Employee.objects.filter(status='active')
    marked = 0

    for emp in active_employees:
        # Check if attendance already exists
        exists = Attendance.objects.filter(
            employee=emp,
            date=yesterday
        ).exists()

        if not exists:
            Attendance.objects.create(
                employee=emp,
                date=yesterday,
                status='absent',
                time_in=None,
                time_out=None,
                admin_override=True,  # bypass weekend check
                notes='Auto-marked absent — no clock-in recorded.',
            )
            marked += 1
            logger.info(f"Marked absent: {emp.get_full_name()} on {yesterday}")

    logger.info(f"Auto-absent complete. {marked} records created for {yesterday}.")
    return marked