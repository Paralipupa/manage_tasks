from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from tasks.models import Task

User = get_user_model()

class AuthenticationTests(APITestCase):
    """Тесты аутентификации"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
        
    def test_user_registration(self):
        """Тест регистрации пользователя"""
        url = reverse('register')
        response = self.client.post(url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')
        
    def test_user_login(self):
        """Тест получения JWT токена"""
        # Создаем пользователя
        User.objects.create_user(**self.user_data)
        
        url = reverse('token_obtain_pair')
        response = self.client.post(url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

class TaskAPITests(APITestCase):
    """Тесты API задач"""
    
    def setUp(self):
        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Получаем токен
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
    def test_create_sum_task(self):
        """Тест создания задачи суммирования"""
        url = reverse('task-list-create')
        data = {
            'task_type': 'sum',
            'input_data': {'a': 10, 'b': 20}
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get().task_type, 'sum')
        
    def test_create_countdown_task(self):
        """Тест создания задачи обратного отсчета"""
        url = reverse('task-list-create')
        data = {
            'task_type': 'countdown',
            'input_data': {'seconds': 5}
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get().task_type, 'countdown')
        
    def test_task_limit(self):
        """Тест ограничения на количество активных задач"""
        url = reverse('task-list-create')
        data = {
            'task_type': 'sum',
            'input_data': {'a': 1, 'b': 1}
        }
        
        # Создаем 5 задач
        for _ in range(5):
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Пытаемся создать шестую задачу
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_task_list_pagination(self):
        """Тест пагинации списка задач"""
        url = reverse('task-list-create')
        data = {
            'task_type': 'sum',
            'input_data': {'a': 1, 'b': 1}
        }
        
        # Создаем 15 задач
        for _ in range(15):
            self.client.post(url, data, format='json')
            
        # Получаем первую страницу
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)  # 10 задач на странице
        self.assertIsNotNone(response.data['next'])  # Есть следующая страница
        
    def test_task_status_filter(self):
        """Тест фильтрации задач по статусу"""
        # Создаем задачи с разными статусами
        Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 1, 'b': 1},
            status=Task.TaskStatus.COMPLETED
        )
        Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 2, 'b': 2},
            status=Task.TaskStatus.PENDING
        )
        
        url = reverse('task-list-create')
        
        # Фильтруем по статусу COMPLETED
        response = self.client.get(f'{url}?status=completed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'completed')
        
    def test_task_user_isolation(self):
        """Тест изоляции задач между пользователями"""
        # Создаем второго пользователя
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        # Создаем задачу от имени первого пользователя
        Task.objects.create(
            user=self.user,
            task_type='sum',
            input_data={'a': 1, 'b': 1}
        )
        
        # Получаем токен для второго пользователя
        refresh = RefreshToken.for_user(other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Проверяем, что второй пользователь не видит задачи первого
        url = reverse('task-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
