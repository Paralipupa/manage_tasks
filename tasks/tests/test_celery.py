from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from tasks.models import Task
from tasks.tasks import process_task

User = get_user_model()

class CeleryTaskTests(TestCase):
    """Тесты для Celery задач"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_sum_task_processing(self):
        """Тест обработки задачи суммирования"""
        task = Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 10, 'b': 20}
        )
        
        # Запускаем задачу
        result = process_task(task.id)
        task.refresh_from_db()
        
        self.assertEqual(task.status, Task.TaskStatus.COMPLETED)
        self.assertEqual(task.result['sum'], 30)
        
    def test_countdown_task_processing(self):
        """Тест обработки задачи обратного отсчета"""
        task = Task.objects.create(
            user=self.user,
            task_type='countdown',
            input_data={'seconds': 1}
        )
        
        # Запускаем задачу
        with patch('time.sleep') as mock_sleep:  # Мокаем time.sleep для ускорения теста
            result = process_task(task.id)
            task.refresh_from_db()
            
            mock_sleep.assert_called_once_with(1)
            self.assertEqual(task.status, Task.TaskStatus.COMPLETED)
            self.assertEqual(task.result['message'], 'Обратный отсчет завершен')
            
    def test_task_error_handling(self):
        """Тест обработки ошибок в задачах"""
        # Создаем задачу с некорректными данными
        task = Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 'not_a_number', 'b': 20}
        )
        
        # Запускаем задачу
        result = process_task(task.id)
        task.refresh_from_db()
        
        self.assertEqual(task.status, Task.TaskStatus.ERROR)
        self.assertIn('error', task.result)
        
    def test_task_state_transitions(self):
        """Тест переходов состояний задачи"""
        task = Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 10, 'b': 20}
        )
        
        self.assertEqual(task.status, Task.TaskStatus.PENDING)
        
        # Запускаем задачу
        result = process_task(task.id)
        task.refresh_from_db()
        
        self.assertEqual(task.status, Task.TaskStatus.COMPLETED)
        
    def test_nonexistent_task(self):
        """Тест обработки несуществующей задачи"""
        with self.assertRaises(Task.DoesNotExist):
            process_task(999)
