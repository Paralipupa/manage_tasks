import os
from celery import Celery
from celery.signals import celeryd_after_setup

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Включаем поддержку запланированных задач
app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,  # Важно для правильной обработки запланированных задач
)

app.autodiscover_tasks()

@celeryd_after_setup.connect
def setup_direct_queue(sender, instance, **kwargs):
    """Настраиваем очередь при запуске воркера"""
    with app.connection() as connection:
        instance.app.amqp.queues.select_add('celery') 