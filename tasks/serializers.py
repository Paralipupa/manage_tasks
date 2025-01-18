from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Task

User = get_user_model()

class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)

class TaskSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    task_type = serializers.ChoiceField(choices=Task.TaskType.choices)
    input_data = serializers.JSONField()
    status = serializers.CharField(read_only=True)
    result = serializers.JSONField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True) 