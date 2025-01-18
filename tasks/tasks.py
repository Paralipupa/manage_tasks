import time
from celery import shared_task
from .models import Task

@shared_task
def process_task(task_id):
    try:
        task = Task.objects.get(id=task_id)
        task.status = Task.TaskStatus.RUNNING
        task.save()

        if task.task_type == Task.TaskType.SUM:
            result = float(task.input_data['a']) + float(task.input_data['b'])
            task.result = {'sum': result}
            
        elif task.task_type == Task.TaskType.COUNTDOWN:
            seconds = int(task.input_data['seconds'])
            time.sleep(seconds)
            task.result = {'message': 'Обратный отсчет завершен'}
            
        task.status = Task.TaskStatus.COMPLETED
        
    except Exception as e:
        task.status = Task.TaskStatus.ERROR
        task.result = {'error': str(e)}
        
    finally:
        task.save()
        
    return task.result 