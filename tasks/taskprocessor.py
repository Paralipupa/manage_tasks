from typing import Any, Union, Optional, Callable, Dict
from django.db import models
from time import sleep


class TaskType(models.TextChoices):
    @classmethod
    def get_choices(cls):
        """Получить список доступных типов задач из процессора"""
        return [(key, key.title()) for key in TaskProcessor.processors.keys()]


class TaskProcessor:
    """Класс для обработки различных типов задач"""

    @staticmethod
    def process_sum(input_data: dict[str, Union[int, float]]) -> dict[str, Any]:
        """Обработка задачи суммирования"""
        try:
            result = sum(input_data["values"])
            return {
                "result": result,
                "message": f'Сумма чисел {",".join(str(x) for x in input_data["values"])} равна {result}',
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
