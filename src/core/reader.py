import re


# Регулярное выражение для одной записи прогресса.
# Время может быть в формате м:сс или ч:мм:сс
PROGRESS_PATTERN = re.compile(
    r"(Testing with random pattern:|Чтение и сравнение:)?\s*"
    r"(\d+\.\d+)%\s+done,\s+(\d+):(\d+):?(\d*)\s+elapsed\.\s*"
    r"\((\d+)/(\d+)/(\d+)\s+errors\)"
)


def parse_elapsed(h1, h2, h3):
    """Разбирает время из групп регулярного выражения и возвращает секунды.

    badblocks печатает прошедшее время:
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
    result = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = text.replace("\b", "\n").replace("\r", "\n")
    fragments = text.split("\n")
    total_blocks = get_total_blocks(text)

    phase_offset = 0.0
    current_phase_name = None

    for fragment in fragments:
        match = PROGRESS_PATTERN.search(fragment)
        if match is None:
            continue

        phase_name = match.group(1)
        if phase_name:
            current_phase_name = phase_name.strip()

        if current_phase_name and "Чтение и сравнение" in current_phase_name:
            if phase_offset == 0.0:
                phase_offset = 100.0

        if "Testing with pattern" in fragment and "random" not in fragment:
            break

        percent = float(match.group(2))
        elapsed = parse_elapsed(match.group(3), match.group(4), match.group(5))

        # Определяем фазу: 1 = запись, 2 = чтение
        current_phase = 2 if phase_offset > 0 else 1

        record = {
            "percent": percent,  # процент этапа (0-100)
            "elapsed": elapsed,  # общее время
            "phase": current_phase,  # 1 или 2
            "errors_new": int(match.group(6)),
            "errors_pre": int(match.group(7)),
            "errors_state": int(match.group(8)),
        }
        result.append(record)
    return result
