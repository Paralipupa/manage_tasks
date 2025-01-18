import time
import json
from celery import shared_task

@shared_task(bind=True)
def process_task(self, task_id):
    """
    Celery задача для обработки асинхронных операций.
    Результат и статус сохраняются в django_celery_results автоматически.
    """
    from .models import Task  # Импорт здесь во избежание циклических импортов
    
    task = Task.objects.get(id=task_id)
    
    try:
        if task.task_type == Task.TaskType.SUM:
            result = float(task.input_data['a']) + float(task.input_data['b'])
            # Сохраняем результат в формате, который можно сериализовать
            self.update_state(state='SUCCESS', meta={'result': result})
            
        elif task.task_type == Task.TaskType.COUNTDOWN:
            seconds = int(task.input_data['seconds'])
            time.sleep(seconds)
            self.update_state(state='SUCCESS', meta={'message': 'Обратный отсчет завершен'})
            
    except Exception as e:
        # В случае ошибки Celery сам обновит статус
        self.update_state(state='FAILURE', meta={'error': str(e)}) 