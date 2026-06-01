from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from .scheduler import auto_mark_absent
        import logging

        logger = logging.getLogger(__name__)

        scheduler = BackgroundScheduler()
        import pytz
        scheduler.add_job(
            auto_mark_absent,
            trigger=CronTrigger(hour=0, minute=5, timezone=pytz.timezone('Asia/Manila')),
            id='auto_mark_absent',
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started — auto-absent will run at 12:05 AM PHT daily.")
        import os
from django.contrib.auth import get_user_model

def ready(self):
    User = get_user_model()

    username = os.getenv("DJANGO_SUPERUSER_USERNAME")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL")

    if username and password:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email or "",
                password=password
            )