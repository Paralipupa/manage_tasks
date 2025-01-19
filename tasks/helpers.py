from django.utils.dateparse import parse_datetime
from django.utils import timezone
import pytz
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from typing import Union


def get_moscow_time(scheduled_at: str) -> Union[datetime, str]:

    # Получаем московский часовой пояс
    moscow_tz = pytz.timezone("Europe/Moscow")

    # Парсим время выполнения
    eta = parse_datetime(scheduled_at)
    if eta is None:
        return "Неверный формат даты и времени"

    # Если дата без часового пояса, считаем её в московском времени
    if timezone.is_naive(eta):
        eta = moscow_tz.localize(eta)

    # Проверяем, что время в будущем
    now = timezone.now().astimezone(moscow_tz)
    if eta <= now:
        return "Дата должна быть в будущем"
    return eta