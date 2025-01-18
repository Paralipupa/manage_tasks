import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django_celery_results.models import TaskResult
from tasks.models import Task

# Фикстуры
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_data():
    return {
        'username': 'testuser',
        'password': 'testpass123',
        'email': 'test@example.com'
    }

@pytest.fixture
def authenticated_client(api_client, django_user_model):
    user = django_user_model.objects.create_user(username='testuser', password='testpass123')
    api_client.force_authenticate(user=user)
    return api_client, user

@pytest.mark.django_db
class TestAuthentication:
    def test_user_registration(self, api_client, user_data, django_user_model):
        url = reverse('register')
        response = api_client.post(url, user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == user_data['username']
        
        user = django_user_model.objects.filter(username=user_data['username']).first()
        assert user is not None
        assert user.email == user_data['email']
        
    def test_user_login(self, api_client, user_data, django_user_model):
        django_user_model.objects.create_user(
            username=user_data['username'],
            password=user_data['password']
        )
        
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

@pytest.mark.django_db
class TestTaskAPI:
    @pytest.fixture
    def sum_task_data(self):
        return {
            'task_type': 'sum',
            'input_data': {'a': 10, 'b': 20}
        }
    
    @pytest.fixture
    def countdown_task_data(self):
        return {
            'task_type': 'countdown',
            'input_data': {'seconds': 5}
        }
    
    def test_create_sum_task(self, authenticated_client, sum_task_data):
        client, user = authenticated_client
        url = reverse('task-list-create')
        
        response = client.post(url, sum_task_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        task = Task.objects.first()
        assert task is not None
        assert task.task_type == 'sum'
        assert task.user == user
        
        # Проверяем, что задача создана в Celery
        celery_task = TaskResult.objects.filter(task_id=task.celery_task_id).first()
        assert celery_task is not None
    
    def test_task_limit(self, authenticated_client, sum_task_data):
        client, _ = authenticated_client
        url = reverse('task-list-create')
        
        # Создаем 5 задач
        for _ in range(5):
            response = client.post(url, sum_task_data)
            assert response.status_code == status.HTTP_201_CREATED
        
        # Пытаемся создать шестую задачу
        response = client.post(url, sum_task_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'превышено' in response.data['error'].lower()
    
    @pytest.mark.parametrize('task_data,expected_error', [
        ({'task_type': 'sum', 'input_data': {'a': 'not_a_number', 'b': 20}}, 'должны быть числами'),
        ({'task_type': 'countdown', 'input_data': {'seconds': -1}}, 'положительным'),
        ({'task_type': 'sum', 'input_data': {}}, 'два числа'),
    ])
    def test_task_validation(self, authenticated_client, task_data, expected_error):
        client, _ = authenticated_client
        url = reverse('task-list-create')
        
        response = client.post(url, task_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_error in response.data['error'].lower()
    
    def test_task_isolation(self, authenticated_client, django_user_model, sum_task_data):
        client1, user1 = authenticated_client
        
        # Создаем второго пользователя и клиента
        user2 = django_user_model.objects.create_user(username='other', password='pass')
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        
        # Создаем задачу от первого пользователя
        url = reverse('task-list-create')
        client1.post(url, sum_task_data)
        
        # Проверяем, что второй пользователь не видит задачу первого
        response = client2.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0
    
    @pytest.mark.django_db(transaction=True)
    def test_task_result_retrieval(self, authenticated_client, sum_task_data, mocker):
        client, _ = authenticated_client
        url = reverse('task-list-create')
        
        # Создаем задачу
        response = client.post(url, sum_task_data)
        task_id = response.data['id']
        
        # Мокаем Celery для немедленного результата
        mocker.patch('tasks.tasks.process_task.delay')
        TaskResult.objects.create(
            task_id=response.data['celery_task_id'],
            status='SUCCESS',
            result={'result': 30}
        )
        
        # Получаем результат
        detail_url = reverse('task-detail', args=[task_id])
        response = client.get(detail_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'SUCCESS'
        assert response.data['result'] == {'result': 30}
