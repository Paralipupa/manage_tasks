from django.db import models
from django.contrib.auth import get_user_model
from django_celery_results.models import TASK_STATE_CHOICES

User = get_user_model()

class Task(models.Model):
    class TaskType(models.TextChoices):
        SUM = 'sum', 'Сумма двух чисел'
        COUNTDOWN = 'countdown', 'Обратный отсчет'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Пользователь'
    )
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        verbose_name='Тип задачи'
    )
    input_data = models.JSONField(
        verbose_name='Входные данные'
    )
    status = models.CharField(
        max_length=50,
        choices=TASK_STATE_CHOICES,
        default='PENDING',
        verbose_name='Статус'
    )
    result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Результат'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task_type} - {self.status} ({self.user.username})'
