from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_type', 'user', 'status', 'created_at', 'scheduled_at')
    list_filter = ('task_type', 'status', 'created_at')
    search_fields = ('user__username', 'task_type', 'status')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'task_type', 'status')
        }),
        ('Данные задачи', {
            'fields': ('input_data', 'result')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'scheduled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == Task.TaskStatus.COMPLETED:
            return False
        return True
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('user', 'task_type', 'input_data')
        return self.readonly_fields

