from enum import Enum
import os


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


TASK_STATUS_MAPPING = {
    TaskStatus.PENDING.value: "Ожидает",
    TaskStatus.STARTED.value: "Выполняется",
    TaskStatus.SUCCESS.value: "Выполнено",
    TaskStatus.FAILURE.value: "Ошибка",
}

TASK_STATUS_CHOICES = [(k, v) for k, v in TASK_STATUS_MAPPING.items()]

# number of active tasks
MAX_ACTIVE_TASKS = os.getenv("MAX_ACTIVE_TASKS", 5)
