from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Task
import pytz
User = get_user_model() # учитывая, что это тестовое задание, ограничимся стандартным пользователем

class UserSerializer(serializers.ModelSerializer):
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
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", default_timezone=pytz.timezone('Europe/Moscow'))
    class Meta:
        model = Task
        fields = ('id', 'user', 'task_type', 'input_data', 'status', 'result', 'created_at')
        read_only_fields = ('status', 'result', 'created_at')

    def validate_input_data(self, value):
        task_type = self.initial_data.get('task_type')
        
        if task_type == Task.TaskType.SUM:
            if not isinstance(value, dict) or 'a' not in value or 'b' not in value:
                raise serializers.ValidationError(
                    'Для задачи суммирования необходимо указать два числа: "a" и "b"'
                )
            try:
                float(value['a'])
                float(value['b'])
            except (TypeError, ValueError):
                raise serializers.ValidationError('Значения должны быть числами')
                
        elif task_type == Task.TaskType.COUNTDOWN:
            if not isinstance(value, dict) or 'seconds' not in value:
                raise serializers.ValidationError(
                    'Для обратного отсчета необходимо указать количество секунд'
                )
            try:
                seconds = int(value['seconds'])
                if seconds <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    'Количество секунд должно быть положительным целым числом'
                )
                
        return value 