import logging
from datetime import timedelta
from django.utils import timezone
import pytz

logger = logging.getLogger(__name__)

def auto_mark_absent():
    """
    Runs daily at midnight Manila time.
    Marks absent ONLY for yesterday Manila time — never today or future.
    Only runs for weekdays (Mon-Fri).
    """
    from .models import Employee, Attendance

    ph_tz = pytz.timezone('Asia/Manila')
    now_ph = timezone.now().astimezone(ph_tz)
    yesterday = now_ph.date() - timedelta(days=1)
    today = now_ph.date()

    # Safety: never mark today or future
    if yesterday >= today:
        logger.warning(f"Safety check failed. Aborting.")
        return 0

    # Skip weekends
    if yesterday.weekday() >= 5:
        logger.info(f"Skipping weekend: {yesterday}")
        return 0

    active_employees = Employee.objects.filter(status='active')
    marked = 0
    for emp in active_employees:
        if emp.date_hired > yesterday:
            continue
        exists = Attendance.objects.filter(employee=emp, date=yesterday).exists()
        if not exists:
            Attendance.objects.create(
                employee=emp,
                date=yesterday,
                status='absent',
                time_in=None,
                time_out=None,
                admin_override=True,
                notes='Auto-marked absent — no clock-in recorded.',
            )
            marked += 1

    logger.info(f"Auto-absent: {marked} records for {yesterday}.")
    return marked