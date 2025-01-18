import pytest
from unittest.mock import patch
from django_celery_results.models import TaskResult
from tasks.models import Task
from tasks.tasks import process_task

@pytest.fixture
def test_user(django_user_model):
    return django_user_model.objects.create_user(
        username='testuser',
        password='testpass123'
    )

@pytest.fixture
def sum_task(test_user):
    return Task.objects.create(
        user=test_user,
        task_type='sum',
        input_data={'a': 10, 'b': 20}
    )

@pytest.fixture
def countdown_task(test_user):
    return Task.objects.create(
        user=test_user,
        task_type='countdown',
        input_data={'seconds': 1}
    )

@pytest.mark.django_db
class TestCeleryTasks:
    def test_sum_task_result(self, sum_task, mocker):
        # Мокаем update_state для проверки результата
        mock_update = mocker.patch('celery.app.task.Task.update_state')
        
        # Запускаем задачу
        process_task(sum_task.id)
        
        # Проверяем, что update_state был вызван с правильными параметрами
        mock_update.assert_called_with(
            state='SUCCESS',
            meta={'result': 30.0}
        )
    
    def test_countdown_task_result(self, countdown_task, mocker):
        # Мокаем time.sleep и update_state
        mocker.patch('time.sleep')
        mock_update = mocker.patch('celery.app.task.Task.update_state')
        
        # Запускаем задачу
        process_task(countdown_task.id)
        
        # Проверяем результат
        mock_update.assert_called_with(
            state='SUCCESS',
            meta={'message': 'Обратный отсчет завершен'}
        )
    
    def test_invalid_task_data(self, sum_task, mocker):
        # Меняем входные данные на некорректные
        sum_task.input_data = {'a': 'not_a_number', 'b': 20}
        sum_task.save()
        
        # Мокаем update_state
        mock_update = mocker.patch('celery.app.task.Task.update_state')
        
        # Запускаем задачу
        process_task(sum_task.id)
        
        # Проверяем, что задача завершилась с ошибкой
        mock_update.assert_called_with(
            state='FAILURE',
            meta={'error': pytest.raises(ValueError).match('.*')}
        )
    
    def test_nonexistent_task(self, mocker):
        # Мокаем update_state
        mock_update = mocker.patch('celery.app.task.Task.update_state')
        
        with pytest.raises(Task.DoesNotExist):
            process_task(999)
        
        # Проверяем, что update_state не вызывался
        mock_update.assert_not_called()
    
    @pytest.mark.django_db(transaction=True)
    def test_task_result_storage(self, sum_task, mocker):
        # Создаем ID для Celery задачи
        celery_task_id = 'test-task-id'
        
        # Мокаем self.request.id в Celery задаче
        mocker.patch('celery.app.task.Task.request').id = celery_task_id
        
        # Запускаем задачу
        process_task(sum_task.id)
        
        # Проверяем, что результат сохранен в TaskResult
        task_result = TaskResult.objects.filter(task_id=celery_task_id).first()
        assert task_result is not None
        assert task_result.status == 'SUCCESS'
        assert task_result.result == {'result': 30.0}
