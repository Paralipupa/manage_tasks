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
                # Парсим время и устанавливаем московскую временную зону
                moscow_tz = pytz.timezone('Europe/Moscow')
                eta = parser.parse(scheduled_at)
                
                # Если время наивное (без временной зоны), считаем его московским
                if eta.tzinfo is None:
                    eta = moscow_tz.localize(eta)
                # Если время в другой временной зоне, конвертируем в московское
                else:
                    eta = eta.astimezone(moscow_tz)
                
                now = timezone.now().astimezone(moscow_tz)
                if eta < now:
                    return Response(
                        {'error': 'Запланированное время не может быть в прошлом (используется московское время)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                eta = None
                
            process_task.apply_async(args=[task.id], eta=eta)
            
        except (ValueError, TypeError):
            return Response(
                {'error': 'Неверный формат времени. Используйте формат "YYYY-MM-DD HH:MM:SS" (московское время)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        if eta:
            response_data['scheduled_at'] = eta.isoformat()
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
