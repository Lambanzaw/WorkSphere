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
        scheduler.add_job(
            auto_mark_absent,
            trigger=CronTrigger(hour=0, minute=5),  # runs at 12:05 AM daily
            id='auto_mark_absent',
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started — auto-absent will run at 12:05 AM daily.")