from django.contrib.auth import get_user_model
from rest_framework import serializers
from django_celery_results.models import TaskResult
from .models import Task

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор для модели задачи"""
    status = serializers.CharField(read_only=True)
    result = serializers.JSONField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Task
        fields = ('id', 'user', 'task_type', 'input_data', 'status', 'result', 'created_at')
        read_only_fields = ('id', 'user', 'status', 'result', 'created_at') 