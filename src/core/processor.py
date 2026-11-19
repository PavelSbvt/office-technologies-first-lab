# -*- coding: utf-8 -*-
"""Модуль обработки данных (core.processor).

Здесь "сырые" записи прогресса badblocks превращаются в данные,
пригодные для анализа и построения графиков:
- сортировка по времени;
- удаление дубликатов и некорректных записей;
- расчёт мгновенной и средней скорости (МБ/с);
- сглаживание (скользящее среднее);
- группировка по интервалам времени и агрегация (средняя скорость).
"""

from utils.utils import bytes_to_mb

# Размер блока в badblocks по умолчанию - 1024 байта.
BLOCK_SIZE = 1024


def clean_records(records):
    """Очищает список записей.

    - сортирует записи по времени elapsed;
    - удаляет записи с нулевым или отрицательным временем;
    - удаляет дубликаты (одинаковое время) и записи, где время
      или процент "пошли назад" (результат обрезков строк в логе).
    """
    records = list(records)
    records.sort(key=lambda r: (r["elapsed"], r["percent"]))

    cleaned = []
    last_elapsed = -1
    last_percent = -1
    for rec in records:
        if rec["elapsed"] <= 0:
            continue  # некорректное значение времени - пропускаем
        if rec["elapsed"] == last_elapsed:
            continue  # дубликат по времени - оставляем первую запись
        if rec["percent"] < last_percent:
            continue  # процент уменьшился - сомнительная запись
        cleaned.append(rec)
        last_elapsed = rec["elapsed"]
        last_percent = rec["percent"]
    return cleaned


def calculate_speeds(records):
    """Дополняет каждую запись расчётными показателями скорости.

    Для каждой пары соседних записей считаем:
    - delta_blocks  - сколько блоков проверено между записями;
    - delta_seconds - сколько секунд на это потребовалось;
    - speed         - мгновенная скорость, МБ/с;
    - avg_speed     - средняя (накопленная) скорость от начала, МБ/с.
    """
    result = []
    prev_block = 0
    prev_time = 0
    for rec in records:
        new_rec = dict(rec)  # копия записи, чтобы не менять исходную

        delta_blocks = rec["block_end"] - prev_block
        delta_seconds = rec["elapsed"] - prev_time

        if delta_seconds > 0 and delta_blocks > 0:
            delta_bytes = delta_blocks * BLOCK_SIZE
            speed_mb = bytes_to_mb(delta_bytes) / delta_seconds
        else:
            speed_mb = 0.0  # нет прироста - скорость неизвестна, считаем 0

        total_bytes = rec["block_end"] * BLOCK_SIZE
        avg_mb = bytes_to_mb(total_bytes) / rec["elapsed"]

        new_rec["speed_mb_s"] = speed_mb
        new_rec["avg_mb_s"] = avg_mb
        result.append(new_rec)

        prev_block = rec["block_end"]
        prev_time = rec["elapsed"]
    return result


def smooth_speeds(records, window=5):
    """Сглаживает мгновенную скорость скользящим средним.

    Возвращает новый список записей, где поле speed_mb_s заменено
    на усреднённое по соседним window записям. Это убирает резкие
    скачки, вызванные округлением процентов в логе.
    """
    result = []
    n = len(records)
    for i in range(n):
        new_rec = dict(records[i])
        start = max(0, i - window // 2)
        end = min(n, i + window // 2 + 1)
        total = 0.0
        count = 0
        for j in range(start, end):
            if records[j]["speed_mb_s"] > 0:
                total = total + records[j]["speed_mb_s"]
                count = count + 1
        if count > 0:
            new_rec["speed_mb_s"] = total / count
        else:
            new_rec["speed_mb_s"] = 0.0
        result.append(new_rec)
    return result


def group_by_interval(records, interval=300):
    """Группирует записи по интервалам времени (по умолчанию 5 минут).

    Для каждого интервала считается средняя скорость - это агрегация
    данных. Возвращает список словарей:
    {"time": середина интервала, "speed": средняя скорость}.
    """
    groups = {}
    for rec in records:
        key = rec["elapsed"] // interval  # номер интервала
        if key not in groups:
            groups[key] = []
        groups[key].append(rec["speed_mb_s"])

    result = []
    keys = sorted(groups.keys())
    for key in keys:
        values = groups[key]
        average = sum(values) / len(values)
        result.append({
            "time": key * interval + interval / 2.0,
            "speed": average,
        })
    return result


def calc_summary(records):
    """Считает итоговые показатели по всем записям (агрегация).

    Возвращает словарь со средней, минимальной и максимальной
    скоростью, а также суммарным количеством ошибок.
    """
    speeds = []
    for rec in records:
        if rec["speed_mb_s"] > 0:
            speeds.append(rec["speed_mb_s"])

    summary = {
        "count": len(records),
        "total_time": 0,
        "avg_speed": 0.0,
        "min_speed": 0.0,
        "max_speed": 0.0,
        "errors": 0,
    }
    if len(records) > 0:
        summary["total_time"] = records[-1]["elapsed"]
        summary["errors"] = (records[-1]["errors_new"] +
                             records[-1]["errors_pre"] +
                             records[-1]["errors_state"])
    if len(speeds) > 0:
        summary["avg_speed"] = sum(speeds) / len(speeds)
        summary["min_speed"] = min(speeds)
        summary["max_speed"] = max(speeds)
    return summary


def process(path):
    """Полная обработка файла: чтение -> очистка -> расчёт -> сглаживание.

    Возвращает кортеж (записи, сводка).
    """
    from src.core.reader import load_raw_lines  # импорт здесь, чтобы не было цикла

    raw = load_raw_lines(path)
    cleaned = clean_records(raw)
    with_speeds = calculate_speeds(cleaned)
    smoothed = smooth_speeds(with_speeds, window=5)
    summary = calc_summary(smoothed)
    return smoothed, summary
