# tasks/tasks.py
from time import sleep
from typing import Any, Union, Optional, Callable, Dict
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from celery import Task as CeleryTask
from .taskstatus import TaskStatus
from .taskprocessor import TaskProcessor

logger = get_task_logger(__name__)


def update_task_state(
    django_task: int,
    state: TaskStatus,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """
    Обновляет состояние задачи в Django

    Args:
        django_task: Экземпляр модели Task Django
        state: Статус задачи
        meta: Дополнительные данные о состоянии задачи
    """
    django_task.status = state
    if meta:
        django_task.result = meta
    django_task.save(update_fields=["status", "result"])
    logger.info(f"Updated task state: {state} for task_id: {django_task.id}")


@shared_task(
    bind=True, max_retries=3, default_retry_delay=60, rate_limit="10/m", acks_late=True
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
        django_task = Task.objects.get(id=task_id)
    except ObjectDoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        raise

    update_task_state(django_task, TaskStatus.STARTED.value)

    try:
        processor = TaskProcessor.get_processor(django_task.task_type)
        result = processor(django_task.input_data)
        update_task_state(django_task, TaskStatus.SUCCESS.value, result)
        return result

    except Exception as e:
        logger.exception(f"Error processing task {task_id}: {str(e)}")
        error_info = {"error": str(e), "error_type": type(e).__name__}
        update_task_state(django_task, TaskStatus.FAILURE.value, error_info)
        raise self.retry(exc=e)
