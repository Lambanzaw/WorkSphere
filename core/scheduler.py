import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

def auto_mark_absent():
    """
    Runs daily at 12:05 AM Manila time (Asia/Manila).
    Marks absent ONLY for yesterday — never for today or future dates.
    Only runs for weekdays (Mon-Fri).
    """
    from .models import Employee, Attendance
    import pytz

    pht = pytz.timezone('Asia/Manila')
    now_pht = timezone.now().astimezone(pht)
    yesterday = now_pht.date() - timedelta(days=1)
    today = now_pht.date()

    # Safety check: never mark today or future dates as absent
    if yesterday >= today:
        logger.warning(f"Safety check failed: yesterday={yesterday}, today={today}. Aborting.")
        return 0

    # Only run for weekdays (Mon=0 to Fri=4)
    if yesterday.weekday() >= 5:
        logger.info(f"Skipping auto-absent for {yesterday} (weekend)")
        return 0

    active_employees = Employee.objects.filter(status='active')
    marked = 0
    for emp in active_employees:
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
            logger.info(f"Marked absent: {emp.get_full_name()} on {yesterday}")

    logger.info(f"Auto-absent complete. {marked} records created for {yesterday}.")
    return marked