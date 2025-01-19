import time
from celery import shared_task
import json
from celery.result import AsyncResult
from rest_framework import generics, status
@shared_task(bind=True)
def process_task(self,task_id):
    """
    Celery задача для обработки асинхронных операций.
    
    Args:
        
        task_id: ID задачи в базе данных Django
    """
    from .models import Task  # Импорт здесь во избежание циклических импортов
    
    # Получаем задачу из базы данных
    django_task = Task.objects.get(id=task_id)
    
    def update_task_state(state, meta=None):
        """Обновляет состояние как в Celery, так и в Django"""
        # task_instance.update_state(state=state, meta=meta)
        django_task.status = state
        if meta:
            django_task.result = meta
        django_task.save()
    
    try:

        if django_task.task_type == Task.TaskType.SUM:
            # Задача суммирования чисел
            a = float(django_task.input_data['a'])
            b = float(django_task.input_data['b'])
            result = a + b
            
            # Сохраняем результат
            update_task_state(
                "SUCCESS",
                {
                    'result': result,
                    'message': f'Сумма чисел {a} и {b} равна {result}'
                }
            )
            
        elif django_task.task_type == Task.TaskType.COUNTDOWN:
            # Задача обратного отсчета
            seconds = int(django_task.input_data['seconds'])
            
            # Обновляем состояние каждую секунду
            time.sleep(seconds)
            
            # Задача завершена
            update_task_state(
                'SUCCESS',
                {
                    'message': 'Обратный отсчет завершен'
                }
            )
            
    except Exception as e:
        # В случае ошибки сохраняем информацию об ошибке
        error_info = {
            'error': str(e),
            'error_type': type(e).__name__
        }
        update_task_state('FAILURE', error_info)
        raise  # Перебрасываем исключение, чтобы Celery отметил задачу как проваленную 