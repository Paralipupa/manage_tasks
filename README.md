# Асинхронная система управления задачами

Тестовое задание: REST API для асинхронного выполнения задач с использованием Django, DRF и Celery.

## Технологии

- Python 3.11
- Django 5.0
- Django REST Framework
- Celery
- Redis
- JWT Authentication

## Установка и запуск

### С использованием Docker

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Запустите проект с помощью Docker Compose:
```bash
docker-compose up --build
```

Приложение будет доступно по адресу: http://localhost:8000

### Локальная установка

1. Создайте и активируйте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Примените миграции:
```bash
python manage.py migrate
```

4. Запустите Redis (необходим для Celery):
```bash
redis-server
```

5. В отдельном терминале запустите Celery:
```bash
celery -A config worker -l INFO
```

6. Запустите Django сервер:
```bash
python manage.py runserver
```

## API Endpoints

### Аутентификация

- `POST /api/register/` - Регистрация нового пользователя
  ```json
  {
    "username": "user",
    "password": "password",
    "email": "user@example.com"
  }
  ```

- `POST /api/token/` - Получение JWT токена
  ```json
  {
    "username": "user",
    "password": "password"
  }
  ```

- `POST /api/token/refresh/` - Обновление JWT токена
  ```json
  {
    "refresh": "refresh_token"
  }
  ```

### Задачи

- `GET /api/tasks/` - Получение списка задач
  - Поддерживает фильтрацию по статусу: `?status=pending`
  - Поддерживает пагинацию

- `POST /api/tasks/` - Создание новой задачи
  ```json
  {
    "task_type": "sum",
    "input_data": {
      "a": 10,
      "b": 20
    }
  }
  ```
  или
  ```json
  {
    "task_type": "countdown",
    "input_data": {
      "seconds": 30
    }
  }
  ```

- `GET /api/tasks/{id}/` - Получение информации о конкретной задаче

## Ограничения

- Пользователь может иметь не более 5 активных задач одновременно
- Поддерживаются два типа задач:
  - `sum` - сложение двух чисел
  - `countdown` - обратный отсчет

## Статусы задач

- `pending` - задача создана и ожидает выполнения
- `running` - задача выполняется
- `completed` - задача успешно завершена
- `error` - произошла ошибка при выполнении задачи 