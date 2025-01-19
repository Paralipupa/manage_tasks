from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters import rest_framework as filters
from django_celery_results.models import TaskResult
from .models import Task
from celery.result import AsyncResult
from .serializers import UserSerializer, TaskSerializer
from .tasks import process_task
from .helpers import get_moscow_time
from django.conf import settings
from typing import Any, Dict
from django.db.models import QuerySet
User = get_user_model()

class UserCreateView(generics.CreateAPIView):
    """Регистрация нового пользователя с автоматической генерацией токена"""
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Создаем токены для пользователя
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': serializer.data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

class TaskFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=[
        ('PENDING', 'Ожидает'),
        ('STARTED', 'Выполняется'),
        ('SUCCESS', 'Выполнено'),
        ('FAILURE', 'Ошибка'),
    ])
    
    class Meta:
        model = Task
        fields = ['status']

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TaskFilter
    
    def get_queryset(self) -> QuerySet[Task]:
        """Получение списка задач текущего пользователя"""
        return Task.objects.filter(user=self.request.user)
    
    def validate_input_data(self, task_type, input_data):
        """Валидация входных данных в зависимости от типа задачи"""
        if task_type == Task.TaskType.SUM:
            if not isinstance(input_data, dict) or 'a' not in input_data or 'b' not in input_data:
                raise ValueError('Для задачи суммирования необходимо указать два числа: "a" и "b"')
            try:
                float(input_data['a'])
                float(input_data['b'])
            except (TypeError, ValueError):
                raise ValueError('Значения должны быть числами')
                
        elif task_type == Task.TaskType.COUNTDOWN:
            if not isinstance(input_data, dict) or 'seconds' not in input_data:
                raise ValueError('Для обратного отсчета необходимо указать количество секунд')
            try:
                seconds = int(input_data['seconds'])
                if seconds <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError('Количество секунд должно быть положительным целым числом')
    
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Создание новой задачи"""
        # Проверяем количество активных задач
        active_tasks = Task.get_active_tasks(request.user).count()
        
        if active_tasks >= 5:
            return Response(
                {'error': 'Превышено максимальное количество активных задач (5)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.validate_input_data(
                serializer.validated_data['task_type'],
                serializer.validated_data['input_data']
            )
            
            # Создаем задачу
            task = Task.objects.create(
                user=request.user,
                **serializer.validated_data
            )
            
            # Получаем время запланированного выполнения из запроса
            # Обновляем статус и результат задачи
            scheduled_at = request.data.get('scheduled_at')
            
            # Запускаем Celery задачу
            if scheduled_at:
                eta = get_moscow_time(scheduled_at)
                if eta is None:
                    return Response("Неверное время")
                # Запускаем задачу с отложенным выполнением
                celery_task = process_task.apply_async((task.id,), eta=eta)
            else:
                # Запускаем задачу немедленно
                celery_task = process_task.delay(task.id)
            
            task.status = AsyncResult(celery_task.id).status
            task.result = celery_task.id
            task.save()

            
            return Response(
                TaskSerializer(task).data,
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self) -> QuerySet[Task]:
        """Получение задач текущего пользователя"""
        return Task.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Получение информации о конкретной задаче"""
        task = self.get_object()
        serializer = self.get_serializer(task)
        if serializer.data['status'] == "SUCCES":
            return Response(serializer.data)
        status = AsyncResult(serializer.data['result']).status
        result = serializer.data.copy()
        result['status'] = status
        return Response(result) 
