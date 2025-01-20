import os
from celery import Celery
from celery.signals import celeryd_after_setup
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Включаем поддержку запланированных задач
app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    enable_utc=True,
    task_always_eager=settings.DEBUG,  # Синхронное выполнение в режиме отладки
    task_default_queue="default",
    task_routes={
        "tasks.tasks.process_task": {"queue": "processor"},
        "tasks.tasks.*": {"queue": "default"},
    },
)

app.autodiscover_tasks()


@celeryd_after_setup.connect
def setup_direct_queue(sender, instance, **kwargs):
    """Настраиваем очередь при запуске воркера"""
    with app.connection() as connection:
        instance.app.amqp.queues.select_add("celery")
