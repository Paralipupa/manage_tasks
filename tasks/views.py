from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import Task
from .serializers import UserSerializer, TaskSerializer
from .tasks import process_task
from django.utils import timezone
import pytz

class UserCreateView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class TaskFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=Task.TaskStatus.choices)
    
    class Meta:
        model = Task
        fields = ['status']

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TaskFilter
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        # Проверяем количество активных задач пользователя
        active_tasks = Task.objects.filter(
            user=request.user,
            status__in=[Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]
        ).count()
        
        if active_tasks >= 5:
            return Response(
                {'error': 'Превышено максимальное количество активных задач (5)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем scheduled_at из запроса, если есть
        scheduled_at = request.data.get('scheduled_at')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        
        # Запускаем задачу асинхронно с учетом запланированного времени
        try:
            if scheduled_at:
                from dateutil import parser
                from datetime import datetime
                import pytz
                
                # Парсим время
                eta = parser.parse(scheduled_at)
                if eta.tzinfo is not None:
                    raise ValueError('Время должно быть без указания временной зоны')
                
                # Проверяем время относительно текущего московского
                moscow_tz = pytz.timezone('Europe/Moscow')
                now = datetime.now(moscow_tz).replace(tzinfo=None)
                
                if eta < now:
                    return Response(
                        {'error': 'Запланированное время не может быть в прошлом'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Сохраняем время в базе как московское (без временной зоны)
                task.scheduled_at = eta
                task.save()
                
                # Для Celery добавляем временную зону к времени
                eta_with_tz = moscow_tz.localize(eta)
                process_task.apply_async(args=[task.id], eta=eta_with_tz)
            else:
                # Если время не указано, выполняем сразу
                process_task.delay(task.id)
            
        except (ValueError, TypeError) as e:
            return Response(
                {'error': str(e) if 'временной зоны' in str(e) else 'Неверный формат времени. Используйте формат "YYYY-MM-DD HH:MM:SS"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        if scheduled_at:
            response_data['scheduled_at'] = eta.strftime('%Y-%m-%d %H:%M:%S')
        else:
            response_data['scheduled_at'] = None
        
        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
