# -*- coding: utf-8 -*-
"""Модуль чтения данных из лог-файла badblocks (core.reader).

Формат строк в файле (badblocks выводит прогресс одной строкой,
перезаписывая её символами возврата каретки \r):

    Checking for bad blocks in read-write mode
    From block 0 to 31330303
    Testing with random pattern:   0.00% done, 0:01 elapsed. (0/0/0 errors)\r
      0.02% done, 0:02 elapsed. (0/0/0 errors)\r ...

Каждая запись прогресса содержит:
- процент выполнения;
- прошедшее время (мм:сс или ч:мм:сс);
- счётчики ошибок (новые/предварительные/состояние) в виде (a/b/c errors).
"""

import re

# Регулярное выражение для одной записи прогресса.
# Время может быть в формате м:сс (например 0:13) или ч:мм:сс (1:02:05).
PROGRESS_PATTERN = re.compile(
    r"(\d+\.\d+)%\s+done,\s+(\d+):(\d+):?(\d*)\s+elapsed\.\s*"
    r"\((\d+)/(\d+)/(\d+)\s+errors\)"
)


def parse_elapsed(h1, h2, h3):
    """Разбирает время из групп регулярного выражения и возвращает секунды.

    badblocks печатает прошедшее время так:
    - пока меньше часа: "м:сс" (например 0:13);
    - когда больше часа: "ч:мм:сс" (например 1:05:09).
    Поэтому если третья группа пустая, формат был "м:сс", иначе "ч:мм:сс".
    """
    if h3 == "":
        minutes = int(h1)
        seconds = int(h2)
        return minutes * 60 + seconds
    hours = int(h1)
    minutes = int(h2)
    seconds = int(h3)
    return hours * 3600 + minutes * 60 + seconds


def get_total_blocks(text):
    """Ищет в тексте строку 'From block 0 to NNN' и возвращает общее число блоков.

    Если строка не найдена, используется значение по умолчанию 31330304
    (карта на 32 ГБ, размер блока 1 КБ).
    """
    pattern = re.compile(r"From block (\d+) to (\d+)")
    match = pattern.search(text)
    if match is not None:
        last_block = int(match.group(2))
        return last_block + 1  # последний блок включительно
    return 31330304


def load_raw_lines(path):
    """Читает файл и возвращает список записей прогресса (словарей).

    Так как badblocks пишет прогресс в одну строку с символами \\r,
    файл читается целиком, затем разбивается по \\r и \\n.
    Из получившихся фрагментов отбираются только те, что похожи на
    запись прогресса - это отсекает мусор и некорректные значения.
    """
    result = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    fragments = text.replace("\r", "\n").split("\n")
    total_blocks = get_total_blocks(text)

    for fragment in fragments:
        match = PROGRESS_PATTERN.search(fragment)
        if match is None:
            continue  # фрагмент не является записью прогресса - пропускаем

        percent = float(match.group(1))
        elapsed = parse_elapsed(match.group(2),
                                match.group(3),
                                match.group(4))
        errors_new = int(match.group(5))
        errors_pre = int(match.group(6))
        errors_state = int(match.group(7))

        record = {
            "percent": percent,                       # % выполнено
            "elapsed": elapsed,                       # время, сек
            "errors_new": errors_new,                 # новые ошибки
            "errors_pre": errors_pre,                 # предварительные ошибки
            "errors_state": errors_state,             # ошибки состояния
            "block_end": int(total_blocks * percent / 100.0),  # номер блока
        }
        result.append(record)

    return result
