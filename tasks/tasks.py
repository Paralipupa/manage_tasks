# tasks/tasks.py
from time import sleep
from typing import Any, Union, Optional
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from enum import Enum
from celery.task import Task as CeleryTask

logger = get_task_logger(__name__)


class TaskStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PROGRESS = "PROGRESS"


def update_task_state(
        celery_task: CeleryTask,
        django_task: 'Task',
        state: TaskStatus,
        meta: Optional[dict[str, Any]] = None
) -> None:
    """
    Обновляет состояние задачи как в Celery, так и в Django

    Args:
        celery_task: Экземпляр задачи Celery
        django_task: Экземпляр модели Task Django
        state: Статус задачи
        meta: Дополнительные данные о состоянии задачи
    """
    celery_task.update_state(state=state, meta=meta)
    django_task.status = state
    if meta:
        django_task.result = meta
    django_task.save(update_fields=['status', 'result'])
    logger.info(f"Updated task state: {state} for task_id: {django_task.id}")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit='10/m',
    acks_late=True
)
def process_task(self: CeleryTask, task_id: int) -> dict[str, Any]:
    """
    Celery задача для обработки асинхронных операций.

    Args:
        task_id: ID задачи в базе данных Django

    Returns:
        dict[str, Any]: Результат выполнения задачи

    Raises:
        ObjectDoesNotExist: Если задача не найдена
        ValueError: При неверных входных данных
    """
    from .models import Task  # Импорт здесь во избежание циклических импортов

    logger.info(f"Starting task processing for task_id: {task_id}")

    try:
        django_task = Task.objects.select_for_update().get(id=task_id)
    except ObjectDoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        raise

    try:
        if django_task.task_type == Task.TaskType.SUM:
            result = process_sum_task(django_task.input_data)
            update_task_state(self, django_task, TaskStatus.SUCCESS, result)

        elif django_task.task_type == Task.TaskType.COUNTDOWN:
            result = process_countdown_task(django_task.input_data)
            update_task_state(self, django_task, TaskStatus.SUCCESS, result)

        else:
            raise ValueError(f"Unknown task type: {django_task.task_type}")

        return result

    except Exception as e:
        logger.exception(f"Error processing task {task_id}: {str(e)}")
        error_info = {
            'error': str(e),
            'error_type': type(e).__name__
        }
        update_task_state(self, django_task, TaskStatus.FAILURE, error_info)
        raise self.retry(exc=e)


def process_sum_task(input_data: list[Union[int, float]]) -> dict[str, Any]:
    """Обработка задачи суммирования"""
    if len(input_data) != 2:
        raise ValueError(f"Invalid input data for sum task: {len(input_data)} numbers in list")
    try:
        result = sum(input_data)
        return {
            'result': result,
            'message': f'Сумма чисел {input_data[0]} и {input_data[1]} равна {result}'
        }
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid input data for sum task: {str(e)}")


def process_countdown_task(input_data: dict[str, int]) -> dict[str, str]:
    """Обработка задачи обратного отсчета"""
    try:
        seconds = int(input_data['seconds'])
        if seconds < 0:
            raise ValueError("Seconds must be positive")
        sleep(seconds)
        return {
            'message': 'Обратный отсчет завершен'
        }
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid input data for countdown task: {str(e)}")