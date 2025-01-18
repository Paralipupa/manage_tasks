from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Task"""
    
    list_display = (
        'id',
        'user',
        'task_type',
        'status',
        'created_at',
    )
    list_filter = ('task_type', 'status', 'created_at')
    search_fields = ('user__username', 'status')
    readonly_fields = ('created_at', 'status', 'result')

