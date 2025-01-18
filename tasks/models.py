from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import pytz

User = get_user_model()

def get_moscow_time():
    """Возвращает текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return timezone.now().astimezone(moscow_tz).replace(tzinfo=None)

class Task(models.Model):
    class TaskStatus(models.TextChoices):
        PENDING = 'pending', 'Запланировано'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Выполнено'
        ERROR = 'error', 'Ошибка'

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
    input_data = models.JSONField(verbose_name='Входные данные')
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
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
