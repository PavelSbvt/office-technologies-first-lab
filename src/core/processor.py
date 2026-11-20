from utils.utils import bytes_to_mb

# Размер блока в badblocks по умолчанию - 1024 байта.
BLOCK_SIZE = 1024
TOTAL_BLOCKS = 31330304


def clean_records(records):
    records = list(records)
    records.sort(key=lambda r: (r["elapsed"], r["percent"]))
    cleaned = []
    last_elapsed = -1
    last_percent = -1
    for rec in records:
        if rec["elapsed"] <= 0:
            continue
        if rec["elapsed"] == last_elapsed:
            cleaned[-1] = rec  # заменяем на более свежую
            continue
        if rec["percent"] < last_percent:  # процент должен расти внутри этапа
            continue
        cleaned.append(rec)
        last_elapsed = rec["elapsed"]
        last_percent = rec["percent"]
    return cleaned


def calculate_speeds(records):
    """Считает скорость внутри одного этапа"""
    result = []
    prev_percent = 0.0
    prev_time = 0

    for rec in records:
        new_rec = dict(rec)

        # Прирост процента внутри текущего этапа
        delta_percent = rec["percent"] - prev_percent
        delta_seconds = rec["elapsed"] - prev_time

        if delta_seconds > 0 and delta_percent > 0:
            delta_blocks = (delta_percent / 100.0) * TOTAL_BLOCKS
            delta_bytes = delta_blocks * BLOCK_SIZE
            speed_mb = bytes_to_mb(delta_bytes) / delta_seconds
        else:
            speed_mb = 0.0

        # Средняя скорость: это среднее по всем записям в этом этапе.
        new_rec["speed_mb_s"] = speed_mb
        # Средняя скорость: кумулятивное среднее
        if "avg_mb_s" not in new_rec:
            new_rec["avg_mb_s"] = speed_mb  # первая точка
        else:
            pass

        result.append(new_rec)
        prev_percent = rec["percent"]
        prev_time = rec["elapsed"]

    # пересчитаем avg_mb_s как кумулятивное среднее
    total_speed = 0.0
    count = 0
    for i, rec in enumerate(result):
        if rec["speed_mb_s"] > 0:
            total_speed += rec["speed_mb_s"]
            count += 1
        if count > 0:
            result[i]["avg_mb_s"] = total_speed / count
        else:
            result[i]["avg_mb_s"] = 0.0

    return result


def process(path):
    from src.core.reader import load_raw_lines
    raw = load_raw_lines(path)

    write_raw = [r for r in raw if r["phase"] == 1]
    read_raw = [r for r in raw if r["phase"] == 2]

    write_cleaned = clean_records(write_raw)
    write_with_speeds = calculate_speeds(write_cleaned)
    write_smoothed = smooth_speeds(write_with_speeds, window=5)
    write_summary = calc_summary(write_smoothed)

    read_cleaned = clean_records(read_raw)
    read_with_speeds = calculate_speeds(read_cleaned)
    read_smoothed = smooth_speeds(read_with_speeds, window=5)
    read_summary = calc_summary(read_smoothed)

    return (write_smoothed, write_summary), (read_smoothed, read_summary)


def smooth_speeds(records, window=5):
    """
    Сглаживает мгновенную скорость кумулятивным средним.

    Возвращает новый список записей, где поле speed_mb_s заменено
    на усреднённое по соседним записям. Это убирает резкие
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
    """Группирует записи по интервалам времени и считает среднюю скорость."""
    groups = {}
    for rec in records:
        key = rec["elapsed"] // interval
        if key not in groups:
            groups[key] = []
        groups[key].append(rec["speed_mb_s"])

    result = []
    keys = sorted(groups.keys())

    # Заполняем пропуски, чтобы интервалы шли непрерывно
    if not keys:
        return result

    min_key, max_key = keys[0], keys[-1]
    last_speed = 0.0

    for key in range(min_key, max_key + 1):
        if key in groups and groups[key]:
            values = groups[key]
            average = sum(values) / len(values)
            last_speed = average
        else:
            # Если данных нет, используем предыдущее значение (или 0)
            average = last_speed

        result.append({
            "time": key * interval + interval / 2.0,
            "speed": average,
        })
    return result


def calc_summary(records):
    """
    Считает итоговые показатели по всем записям (агрегация).

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
