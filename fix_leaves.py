import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worksphere.settings')
django.setup()

from core.models import Employee, LeaveBalance, LeaveType
from django.utils import timezone

year = timezone.now().year

# Update leave types with correct max_days
updates = {
    'Sick Leave': 20,
    'Vacation Leave': 10,
    'Maternity Leave': 10,
    'Paternity Leave': 10,
    'Emergency Leave': 3,
}

for name, days in updates.items():
    lt, created = LeaveType.objects.get_or_create(name=name, defaults={'max_days': days})
    if not created:
        lt.max_days = days
        lt.save()
    print(f"{'Created' if created else 'Updated'} LeaveType: {name} -> {days} days")

# Allocate balances per employee respecting gender
employees = Employee.objects.filter(status='active')

for emp in employees:
    for lt in LeaveType.objects.all():
        # Remove Maternity for male
        if lt.name == 'Maternity Leave' and emp.gender == 'male':
            LeaveBalance.objects.filter(employee=emp, leave_type=lt, year=year).delete()
            print(f"Removed Maternity Leave for {emp.get_full_name()} (male)")
            continue
        # Remove Paternity for female
        if lt.name == 'Paternity Leave' and emp.gender == 'female':
            LeaveBalance.objects.filter(employee=emp, leave_type=lt, year=year).delete()
            print(f"Removed Paternity Leave for {emp.get_full_name()} (female)")
            continue

        bal, created = LeaveBalance.objects.get_or_create(
            employee=emp,
            leave_type=lt,
            year=year,
            defaults={'allocated_days': lt.max_days}
        )
        if not created:
            bal.allocated_days = lt.max_days
            bal.save()
        print(f"{'Created' if created else 'Updated'}: {emp.get_full_name()} ({emp.gender}) - {lt.name} -> {lt.max_days} days")

print("\nDone!")