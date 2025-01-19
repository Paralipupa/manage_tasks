# tasks/tasks.py
from time import sleep
from typing import Any, Union, Optional, Callable, Dict
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from celery import Task as CeleryTask
from .taskstatus import TaskStatus

logger = get_task_logger(__name__)


class TaskProcessor:
    """Класс для обработки различных типов задач"""

    @staticmethod
    def process_sum(input_data: dict[str, Union[int, float]]) -> dict[str, Any]:
        """Обработка задачи суммирования"""
        try:
            result = sum(input_data.values())
            return {
                "result": result,
                "message": f'Сумма чисел {",".join(str(x) for x in input_data.values())} равна {result}',
            }
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid input data for sum task: {str(e)}")

    @staticmethod
    def process_countdown(input_data: dict[str, int]) -> dict[str, str]:
        """Обработка задачи обратного отсчета"""
        try:
            seconds = int(input_data["seconds"])
            if seconds < 0:
                raise ValueError("Seconds must be positive")
            sleep(seconds)
            return {"message": "Обратный отсчет завершен"}
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid input data for countdown task: {str(e)}")

    # Маппинг типов задач к методам-обработчикам
    processors: Dict[str, Callable] = {
        "sum": process_sum,
        "countdown": process_countdown,
    }

    @classmethod
    def get_processor(cls, task_type: str) -> Callable:
        """Получить функцию-обработчик для заданного типа задачи"""
        processor = cls.processors.get(task_type)
        if not processor:
            raise ValueError(f"Unknown task type: {task_type}")
        return processor


def update_task_state(
    celery_task: CeleryTask,
    django_task: int,
    state: TaskStatus,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """
    Обновляет состояние задачи как в Celery, так и в Django

    Args:
        celery_task: Экземпляр задачи Celery
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

    update_task_state(self, django_task, TaskStatus.STARTED.value)

    try:
        processor = TaskProcessor.get_processor(django_task.task_type)
        result = processor(django_task.input_data)
        update_task_state(self, django_task, TaskStatus.SUCCESS.value, result)
        return result

    except Exception as e:
        logger.exception(f"Error processing task {task_id}: {str(e)}")
        error_info = {"error": str(e), "error_type": type(e).__name__}
        update_task_state(self, django_task, TaskStatus.FAILURE.value, error_info)
        raise self.retry(exc=e)
