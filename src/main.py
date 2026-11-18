# -*- coding: utf-8 -*-
"""Точка входа приложения (main.py).

Лабораторная работа №1. Обработка и визуализация данных.
Вариант 3: графики скорости по лог-файлу программы badblocks.

Запуск:
    python main.py                     - открыть графическое окно
    python main.py путь/к/файлу.bbl    - сразу обработать указанный файл
    python main.py --nogui             - без окна: обработать и сохранить
                                         графики в папку output
"""

import os
import sys


def get_default_path():
    """Возвращает путь к демонстрационному файлу данных."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "data", "Kingston-SD-32G.bbl")


def run_console(path):
    """Обрабатывает файл без графического окна и сохраняет графики."""
    from src.core.processor import process
    from src.core.charts import build_all_figures, save_all_figures
    from src.core.utils import format_time

    print("Читаем файл: {}".format(path))
    records, summary = process(path)
    if len(records) < 3:
        print("Ошибка: в файле найдено слишком мало корректных записей.")
        return 1

    print("Записей после обработки: {}".format(summary["count"]))
    print("Время проверки: {} ({} сек)".format(
        format_time(summary["total_time"]), summary["total_time"]))
    print("Средняя скорость: {:.2f} МБ/с".format(summary["avg_speed"]))
    print("Минимальная скорость: {:.2f} МБ/с".format(summary["min_speed"]))
    print("Максимальная скорость: {:.2f} МБ/с".format(summary["max_speed"]))
    print("Ошибок: {}".format(summary["errors"]))

    figures = build_all_figures(records)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(base_dir, "output")
    paths = save_all_figures(figures, folder)
    print("Графики сохранены:")
    for name, file_path in paths:
        print("- {} -> {}".format(name, file_path))
    return 0


def main():
    args = sys.argv[1:]
    nogui = False
    path = ""

    # Разбираем аргументы командной строки.
    for arg in args:
        if arg == "--nogui":
            nogui = True
        else:
            path = arg
    if path == "":
        path = get_default_path()

    if nogui:
        return run_console(path)

    try:
        from src.gui.window import run
        run(path)
    except Exception as exc:
        # Если окно открыть нельзя (нет дисплея/Tkinter), работаем в консоли.
        print("Не удалось открыть графическое окно: {}".format(exc))
        print("Перехожу в консольный режим...")
        return run_console(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
