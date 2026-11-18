# -*- coding: utf-8 -*-
"""Вспомогательные функции (модуль utils).

Здесь находятся простые функции, которые используются другими модулями:
перевод байт в удобочитаемый вид и форматирование времени.
"""


def format_bytes(num_bytes):
    """Переводит количество байт в человекочитаемый вид.

    Например: 1048576 -> "1.00 МБ".
    """
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    value = float(num_bytes)
    index = 0
    while value >= 1024.0 and index < len(units) - 1:
        value = value / 1024.0
        index = index + 1
    return "{:.2f} {}".format(value, units[index])


def bytes_to_mb(num_bytes):
    """Переводит байты в мегабайты."""
    return num_bytes / (1024.0 * 1024.0)


def format_time(seconds):
    """Форматирует время в виде ч:мм:сс.

    Например: 3725 -> "1:02:05".
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return "{}:{:02d}:{:02d}".format(hours, minutes, secs)
