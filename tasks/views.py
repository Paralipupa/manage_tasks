from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters import rest_framework as filters
from django_celery_results.models import TaskResult
from contextlib import suppress
from .models import Task
from celery.result import AsyncResult
from .serializers import UserSerializer, TaskSerializer
from .tasks import process_task
from .helpers import get_moscow_time
from django.conf import settings
from typing import Any
from django.db.models import QuerySet
from .taskstatus import TaskStatus, TASK_STATUS_CHOICES, MAX_ACTIVE_TASKS

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

        return Response(
            {
                "user": serializer.data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class TaskFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=TASK_STATUS_CHOICES)

    class Meta:
        model = Task
        fields = ["status"]


class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TaskFilter

    def get_queryset(self) -> QuerySet[Task]:
        """Получение списка задач текущего пользователя"""
        return Task.objects.filter(user=self.request.user)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Создание новой задачи"""

        # Проверяем количество активных задач
        if Task.get_active_tasks(request.user).count() >= MAX_ACTIVE_TASKS:
            return Response(
                {
                    "error": f"Превышено максимальное количество активных задач ({MAX_ACTIVE_TASKS})"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Создаем задачу
            task = Task.objects.create(user=request.user, **serializer.validated_data)
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        if serializer.data["status"] == TaskStatus.SUCCESS.value:
            return Response(serializer.data)
        proc = AsyncResult(serializer.data["result"])
        result = serializer.data.copy()
        try:
            result["status"] = proc.status
        except Exception as e:
            # если статус не равен failure, то устанавливаем его и сохраняем ошибку
            if result["status"] != TaskStatus.FAILURE.value:
                result["status"] = TaskStatus.FAILURE.value
                result["result"] = str(e)
        return Response(result)

