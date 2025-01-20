from django.db import models
from django.contrib.auth import get_user_model
from django_celery_results.models import TASK_STATE_CHOICES
from django.db.models import QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver
from .taskstatus import TaskStatus
from .taskprocessor import TaskProcessor, TaskType
from .tasks import process_task
from .helpers import get_moscow_time

User = get_user_model()


class Task(models.Model):
    """Модель для хранения информации о задачах"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Пользователь",
    )
    task_type = models.CharField(
        max_length=20, choices=TaskType.get_choices(), verbose_name="Тип задачи"
    )
    input_data = models.JSONField(verbose_name="Входные данные")
    status = models.CharField(
        max_length=50,
        choices=TASK_STATE_CHOICES,
        default="PENDING",
        verbose_name="Статус",
    )
    result = models.JSONField(null=True, blank=True, verbose_name="Результат")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_task_type_display()} - {self.status} ({self.user.username})"

    @staticmethod
    def get_active_tasks(user) -> QuerySet:
        return Task.objects.filter(
            user=user,
            status__in=[
                TaskStatus.PENDING.value,
                TaskStatus.STARTED.value,
            ],
        )

@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    """Обработчик сигнала post_save для модели Task"""
    if created and not hasattr(instance, '_task_post_save_processed'):
        # Устанавливаем флаг, что мы уже обработали этот инстанс
        instance._task_post_save_processed = True
        
        # При создании записываем входные данные в result
        instance.result = instance.input_data
        
        # Получаем время запланированного выполнения
        scheduled_at = instance.input_data.get('scheduled_at')
        
        if scheduled_at:
            eta = get_moscow_time(scheduled_at)
            if not isinstance(eta, str):
                # Запускаем задачу с отложенным выполнением
                celery_task = process_task.apply_async((instance.id,), eta=eta)
                # Обновляем статус и ID задачи
                instance.status = celery_task.status
                instance.result = celery_task.id
                instance.save(update_fields=['status', 'result'])
        else:
            # Запускаем задачу немедленно
            celery_task = process_task.delay(instance.id)
            # Обновляем статус и ID задачи
            instance.status = celery_task.status
            instance.result = celery_task.id
            instance.save(update_fields=['status', 'result'])
